import unittest
from typing import Any
from unittest.mock import MagicMock, patch

from google.cloud import logging
from google.cloud.exceptions import NotFound

from wanna.core.deployment.models import LogMetricResource
from wanna.core.deployment.vertex_connector import VertexConnector


class TestMonitoring(unittest.TestCase):
    common_resource_fields = {
        "project": "test-project",
        "location": "europe-west-1",
        "service_account": "test@test-project.iam.gserviceaccount.com",
    }
    connector = VertexConnector[Any]()

    @patch("wanna.core.deployment.monitoring.waiting")
    @patch("wanna.core.deployment.monitoring.gcloud_logging")
    def test_upsert_log_metric_waits_after_creation(self, mock_logging_module, mock_waiting):
        """Test that upsert_log_metric waits for metric creation using waiting.wait."""
        # Setup resource
        resource = LogMetricResource(
            name="test-log-metric",
            filter_="resource.type=cloud_function",
            description="Test log metric",
            **self.common_resource_fields,
        )

        # Mock logging client and metrics_api
        mock_client = MagicMock(spec=logging.Client)
        mock_metrics_api = MagicMock()
        mock_client.metrics_api = mock_metrics_api
        mock_logging_module.Client.return_value = mock_client

        # First call to metric_get raises NotFound (metric doesn't exist)
        # Second call (inside wait lambda) returns the metric (metric created)
        # Third call (after wait) returns the metric
        created_metric = {"name": "test-log-metric", "filter": "resource.type=cloud_function"}
        mock_metrics_api.metric_get.side_effect = [
            NotFound("Metric not found"),  # First call - triggers creation
            created_metric,  # Second call - inside wait lambda
            created_metric,  # Third call - after wait
        ]

        # Mock waiting.wait
        mock_waiting.wait = MagicMock()

        # Execute
        result = self.connector.upsert_log_metric(resource)

        # Verify metric_create was called
        mock_metrics_api.metric_create.assert_called_once_with(
            project=resource.project,
            metric_name=resource.name,
            filter_=resource.filter_,
            description=resource.description,
        )

        # Verify waiting.wait was called with correct parameters (lines 171-178)
        mock_waiting.wait.assert_called_once()
        call_args = mock_waiting.wait.call_args

        # Verify the lambda function calls metric_get with correct parameters
        lambda_func = call_args[0][0]
        lambda_result = lambda_func()
        assert lambda_result == created_metric
        assert call_args[1]["timeout_seconds"] == 120
        assert call_args[1]["sleep_seconds"] == 5
        assert call_args[1]["waiting_for"] == "Log metric"

        # Verify final metric_get was called
        assert mock_metrics_api.metric_get.call_count == 3
        assert result == created_metric
