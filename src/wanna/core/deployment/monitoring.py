import json
from typing import Optional, cast

from google.cloud.exceptions import NotFound
from google.cloud.logging import Client as LoggingClient
from google.cloud.monitoring_v3 import (
    AlertPolicy,
    AlertPolicyServiceClient,
    NotificationChannel,
    NotificationChannelServiceClient,
)

from wanna.core.deployment.credentials import GCPCredentialsMixIn
from wanna.core.deployment.models import AlertPolicyResource, LogMetricResource, NotificationChannelResource


class MonitoringMixin(GCPCredentialsMixIn):
    @staticmethod
    def _get_notification_channel(
        client: NotificationChannelServiceClient, project: str, display_name: str
    ) -> Optional[NotificationChannel]:
        channels = list(client.list_notification_channels(name=f"projects/{project}"))
        channels = [channel for channel in channels if channel.display_name == display_name]
        if channels:
            return channels[0]
        return None

    def upsert_notification_channel(self, resource: NotificationChannelResource):
        client = NotificationChannelServiceClient(credentials=self.credentials)

        channel = MonitoringMixin._get_notification_channel(client, resource.project, resource.name)

        if not channel:
            notification_channel = NotificationChannel(
                type_=resource.type_,
                display_name=resource.name,
                description="",
                labels=resource.config,
                user_labels=resource.labels,
                verification_status=NotificationChannel.VerificationStatus.VERIFIED,
                enabled=True,
            )
            return client.create_notification_channel(
                name=f"projects/{resource.project}", notification_channel=notification_channel
            )
        else:
            return channel

    def upsert_alert_policy(self, resource: AlertPolicyResource):
        client = AlertPolicyServiceClient(credentials=self.credentials)

        alert_policy = {
            "display_name": resource.display_name,
            "user_labels": resource.labels,
            "conditions": [
                {
                    "display_name": "Failed scheduling",
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

        alert_policy = cast(AlertPolicy, AlertPolicy.from_json(json.dumps(alert_policy)))
        policies = client.list_alert_policies(name=f"projects/{resource.project}")
        policy = [policy for policy in policies if policy.display_name == resource.name]
        if policy:
            policy = policy[0]
            alert_policy.name = policy.name
            client.update_alert_policy(alert_policy=alert_policy)
        else:
            client.create_alert_policy(name=f"projects/{resource.project}", alert_policy=alert_policy)

    def upsert_log_metric(self, resource: LogMetricResource):
        client = LoggingClient(credentials=self.credentials)
        try:
            client.metrics_api.metric_get(project=resource.project, metric_name=resource.name)
        except NotFound as e:
            print(e)
            client.metrics_api.metric_create(
                project=resource.project,
                metric_name=resource.name,
                filter_=resource.filter_,
                description=resource.description,
            )
