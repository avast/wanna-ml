from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, cast

from lazyimport import Import

if TYPE_CHECKING:  # pragma: no cover
    import google.cloud.exceptions as gcloud_exceptions
    import google.cloud.logging as gcloud_logging
    import google.cloud.monitoring_v3 as gcloud_monitoring_v3
    import google.cloud.pubsub_v1 as gcloud_pubsub_v1
    from waiting import wait
else:
    gcloud_exceptions = Import("google.cloud.exceptions")
    gcloud_logging = Import("google.cloud.logging")
    gcloud_monitoring_v3 = Import("google.cloud.monitoring_v3")
    gcloud_pubsub_v1 = Import("google.cloud.pubsub_v1")
    wait = Import("waiting.wait")

from wanna.core.deployment.credentials import GCPCredentialsMixIn
from wanna.core.deployment.models import (
    AlertPolicyResource,
    LogMetricResource,
    NotificationChannelResource,
)
from wanna.core.loggers.wanna_logger import get_logger

logger = get_logger(__name__)


class MonitoringMixin(GCPCredentialsMixIn):
    @staticmethod
    def _get_notification_channel(
        client: gcloud_monitoring_v3.NotificationChannelServiceClient,
        project: str,
        display_name: str,
    ) -> gcloud_monitoring_v3.NotificationChannel | None:
        channels = list(client.list_notification_channels(name=f"projects/{project}"))
        channels = [channel for channel in channels if channel.display_name == display_name]
        if channels:
            return channels[0]
        return None

    def require_pubsub_topic(self, project_id: str, topic_id: str) -> None:
        """
        Check if a Pubsub topic exists. Raises NotFound if it does not exist.

        Args:
            project_id: GCP project ID
            topic_id: Pubsub topic ID (not the full path)

        Raises:
            NotFound: If the topic does not exist
        """
        client = gcloud_pubsub_v1.PublisherClient(credentials=self.credentials)
        topic_path = client.topic_path(project_id, topic_id)

        try:
            client.get_topic(topic=topic_path)
            logger.user_info(f"Found existing Pubsub topic: {topic_path}")
        except gcloud_exceptions.NotFound as e:
            logger.user_info(f"Pubsub topic not found: {topic_path}")
            raise e

    def upsert_notification_channel(self, resource: NotificationChannelResource):
        client = gcloud_monitoring_v3.NotificationChannelServiceClient(
            credentials=self.credentials
        )

        channel = MonitoringMixin._get_notification_channel(
            client, resource.project, resource.name
        )
        if resource.type_ == "pubsub" and "topic" in resource.config:
            topic_path = resource.config["topic"]
            parts = topic_path.split("/")
            if len(parts) == 4 and parts[0] == "projects" and parts[2] == "topics":
                project_id = parts[1]
                topic_id = parts[3]
                self.require_pubsub_topic(project_id, topic_id)

        if not channel:
            with logger.user_spinner(f"Creating notification channel: {resource.name}"):
                notification_channel = gcloud_monitoring_v3.NotificationChannel(
                    type_=resource.type_,
                    display_name=resource.name,
                    description=resource.description,
                    labels=resource.config,
                    user_labels=resource.labels,
                    verification_status=gcloud_monitoring_v3.NotificationChannel.VerificationStatus.VERIFIED,
                    enabled=True,
                )
                return client.create_notification_channel(
                    name=f"projects/{resource.project}",
                    notification_channel=notification_channel,
                )
        else:
            logger.user_info(f"Found existing notification channel: {resource.name}")
            return channel

    def upsert_alert_policy(self, resource: AlertPolicyResource):
        client = gcloud_monitoring_v3.AlertPolicyServiceClient(credentials=self.credentials)

        alert_policy = {
            "display_name": resource.display_name,
            "user_labels": resource.labels,
            "conditions": [
                {
                    "display_name": "Error detected",
                    "condition_threshold": {
                        # https://issuetracker.google.com/issues/143436657?pli=1
                        # resource.type must be defined based on the resource type from log metric
                        "filter": f"""
                            metric.type="logging.googleapis.com/user/{resource.logging_metric_type}"
                            AND resource.type="{resource.resource_type}"
                            """,
                        "aggregations": [
                            {
                                "alignment_period": "600s",
                                "cross_series_reducer": "REDUCE_SUM",
                                "per_series_aligner": "ALIGN_DELTA",
                            }
                        ],
                        "comparison": "COMPARISON_GT",
                        "duration": "0s",
                        "trigger": {"count": 1},
                        "threshold_value": 0,
                    },
                }
            ],
            "alert_strategy": {
                "auto_close": "604800s",
            },
            "combiner": "OR",
            "enabled": True,
            "notification_channels": resource.notification_channels,
        }

        alert_policy = cast(
            gcloud_monitoring_v3.AlertPolicy,
            gcloud_monitoring_v3.AlertPolicy.from_json(json.dumps(alert_policy)),
        )
        policies = client.list_alert_policies(name=f"projects/{resource.project}")
        policy = [policy for policy in policies if policy.display_name == resource.name]
        if policy:
            policy = policy[0]
            alert_policy.name = policy.name
            with logger.user_spinner(f"Updating alert policy: {alert_policy.name}"):
                client.update_alert_policy(alert_policy=alert_policy)
        else:
            with logger.user_spinner(f"Creating alert policy: {alert_policy.name}"):
                client.create_alert_policy(
                    name=f"projects/{resource.project}", alert_policy=alert_policy
                )

    def upsert_log_metric(self, resource: LogMetricResource) -> dict[str, Any]:
        client = gcloud_logging.Client(credentials=self.credentials)
        try:
            logger.user_info(f"Found existing log metric: {resource.name}")
            return client.metrics_api.metric_get(
                project=resource.project, metric_name=resource.name
            )
        except gcloud_exceptions.NotFound:
            client.metrics_api.metric_create(
                project=resource.project,
                metric_name=resource.name,
                filter_=resource.filter_,
                description=resource.description,
            )
            with logger.user_spinner(f"Creating log metric: {resource.name}"):
                wait(
                    lambda: client.metrics_api.metric_get(
                        project=resource.project, metric_name=resource.name
                    ),
                    timeout_seconds=120,
                    sleep_seconds=5,
                    waiting_for="Log metric",
                )
            return client.metrics_api.metric_get(
                project=resource.project, metric_name=resource.name
            )
