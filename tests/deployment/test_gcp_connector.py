import os
import unittest
from pathlib import Path
from typing import Any

from google.cloud import logging, scheduler_v1
from google.cloud.functions_v1 import CloudFunctionsServiceClient
from google.cloud.monitoring_v3 import AlertPolicyServiceClient, NotificationChannel, NotificationChannelServiceClient
from mock import MagicMock

from wanna.core.deployment.models import CloudFunctionResource, CloudSchedulerResource, NotificationChannelResource
from wanna.core.deployment.vertex_connector import VertexConnector
from wanna.core.models.cloud_scheduler import CloudSchedulerModel


class TestGCPConnector(unittest.TestCase):
    common_resource_fields = {
        "project": "test_notification_channel",
        "location": "europe-west-1",
        "service_account": "wanna-dev@yourproject.iam.gserviceaccount.com",
    }
    parent = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
    build_dir = parent / "build"
    version = "test"
    env = "test"
    connector = VertexConnector[Any]()

    def test_upsert_notification_channel(self):
        notification_channel_resource = NotificationChannelResource(
            name="test_notification_channel",
            type_="email",
            config={"email_address": "john.doe@domain.com"},
            labels={},
            **self.common_resource_fields,
        )

        expected_notification_channel = NotificationChannel(
            type_="email",
            display_name="test_notification_channel",
            description="",
            labels={"email_address": "john.doe@domain.com"},
            user_labels={},
            verification_status=NotificationChannel.VerificationStatus.VERIFIED,
            enabled=True,
        )

        NotificationChannelServiceClient.list_notification_channels = MagicMock(return_value=[])
        NotificationChannelServiceClient.create_notification_channel = MagicMock()
        self.connector.upsert_notification_channel(notification_channel_resource)

        NotificationChannelServiceClient.list_notification_channels.assert_called_with(
            name="projects/test_notification_channel"
        )
        NotificationChannelServiceClient.create_notification_channel.assert_called_with(
            name="projects/test_notification_channel", notification_channel=expected_notification_channel
        )

    def test_upsert_cloud_function(self):
        resource_root = "gs://wanna-ml/deployment/dev"
        resource = CloudFunctionResource(
            name="test-function",
            build_dir=self.build_dir,
            resource_root=resource_root,
            resource_function_template="scheduler_cloud_function.py",
            resource_requirements_template="scheduler_cloud_function_requirements.txt",
            template_vars={},
            env_params={},
            labels={},
            network="default",
            notification_channels=["projects/"],
            **self.common_resource_fields,
        )
        expected_function_name = (
            "projects/test_notification_channel/locations/europe-west-1/functions/test-function-test"
        )
        expected_function = {
            "name": expected_function_name,
            "description": "wanna test-function function for test pipeline",
            "source_archive_url": f"{resource_root}/functions/package.zip",
            "entry_point": "process_request",
            "runtime": "python39",
            "https_trigger": {
                "url": "https://europe-west-1-test_notification_channel.cloudfunctions.net/test-function-test",
            },
            "service_account_email": "wanna-dev@yourproject.iam.gserviceaccount.com",
            "labels": {},
            "environment_variables": {},
        }

        # Set Mocks
        AlertPolicyServiceClient.list_alert_policies = MagicMock(return_value=[])
        AlertPolicyServiceClient.update_alert_policy = MagicMock()
        AlertPolicyServiceClient.create_alert_policy = MagicMock()
        logging.Client.metrics_api.metric_create = MagicMock()
        logging.Client.metrics_api.metric_get = MagicMock()
        CloudFunctionsServiceClient.get_function = MagicMock()
        CloudFunctionsServiceClient.update_function = MagicMock()

        function_path, function_url = self.connector.upsert_cloud_function(
            resource=resource, version=self.version, env=self.env
        )

        self.assertEqual(
            function_path, "projects/test_notification_channel/locations/europe-west-1/functions/test-function-test"
        )
        self.assertEqual(
            function_url, "https://europe-west-1-test_notification_channel.cloudfunctions.net/test-function-test"
        )

        # Check cloudfunctions sdk methos were called with expected function params
        CloudFunctionsServiceClient.get_function.assert_called_with(
            {"name": "projects/test_notification_channel/locations/europe-west-1/functions/test-function-test"}
        )
        CloudFunctionsServiceClient.update_function.assert_called_with({"function": expected_function})

        AlertPolicyServiceClient.list_alert_policies.assert_called()
        AlertPolicyServiceClient.create_alert_policy.assert_called()

    def test_upsert_cloud_scheduler(self):
        function_refs = (
            "projects/test_notification_channel/locations/europe-west-1/functions/test-function-test",
            "https://europe-west-1-test_notification_channel.cloudfunctions.net/test-function-test",
        )
        resource = CloudSchedulerResource(
            name="test-cloud-scheduler-job",
            cloud_scheduler=CloudSchedulerModel(cron="0 * * * *"),
            body={},
            labels={},
            notification_channels=[],
            **self.common_resource_fields,
        )

        AlertPolicyServiceClient.list_alert_policies = MagicMock(return_value=[])
        AlertPolicyServiceClient.update_alert_policy = MagicMock()
        AlertPolicyServiceClient.create_alert_policy = MagicMock()
        logging.Client.metrics_api.metric_create = MagicMock()
        logging.Client.metrics_api.metric_get = MagicMock()
        scheduler_v1.CloudSchedulerClient.get_job = MagicMock()
        scheduler_v1.CloudSchedulerClient.update_job = MagicMock()
        NotificationChannelServiceClient.list_notification_channels = MagicMock(return_value=[])
        NotificationChannelServiceClient.create_notification_channel = MagicMock()

        self.connector.upsert_cloud_scheduler(
            function=function_refs, resource=resource, version=self.version, env=self.env
        )

        job_name = "projects/test_notification_channel/locations/europe-west-1/jobs/test-cloud-scheduler-job-test"
        scheduler_v1.CloudSchedulerClient.get_job.assert_called_once()
        scheduler_v1.CloudSchedulerClient.update_job.assert_called_once()
        scheduler_v1.CloudSchedulerClient.get_job.assert_called_with({"name": job_name})
