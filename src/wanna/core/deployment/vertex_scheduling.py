import json
import os
import zipfile
from pathlib import Path
from typing import Tuple

from caseconverter import snakecase
from google.api_core.exceptions import PermissionDenied
from google.cloud import scheduler_v1
from google.cloud.exceptions import NotFound
from google.cloud.functions_v1 import CloudFunctionsServiceClient

from wanna.core.deployment.io import IOMixin
from wanna.core.deployment.models import (
    AlertPolicyResource,
    CloudFunctionResource,
    CloudSchedulerResource,
    LogMetricResource,
)
from wanna.core.deployment.monitoring import MonitoringMixin
from wanna.core.loggers.wanna_logger import get_logger
from wanna.core.utils import templates
from wanna.core.utils.gcp import is_gcs_path

logger = get_logger(__name__)


class VertexSchedulingMixIn(MonitoringMixin, IOMixin):
    def upsert_cloud_scheduler(
        self,
        function: Tuple[str, str],
        resource: CloudSchedulerResource,
        version: str,
        env: str,
    ) -> None:
        client = scheduler_v1.CloudSchedulerClient(credentials=self.credentials)
        parent = f"projects/{resource.project}/locations/{resource.location}"
        job_id = f"{resource.name}-{env}"
        job_name = f"{parent}/jobs/{job_id}"
        function_name, function_url = function

        logger.user_info(
            f"Deploying {resource.name} cloud scheduler with version {version} to env {env}"
        )

        http_target = {
            "uri": function_url,
            "body": json.dumps(resource.body, separators=(",", ":")).encode(),
            "headers": {
                "Content-Type": "application/octet-stream",
                "User-Agent": "Google-Cloud-Scheduler",
                "Wanna-Pipeline-Version": version,
            },
            "oidc_token": {
                "service_account_email": resource.cloud_scheduler.service_account
                or resource.service_account,
                # required scope https://developers.google.com/identity/protocols/oauth2/scopes#cloudfunctions
                # "scope": "https://www.googleapis.com/auth/cloud-platform"
            },
        }

        job = {
            "name": job_name,
            "description": f"wanna {resource.name} scheduler for  {env} pipeline",
            "http_target": http_target,
            "schedule": resource.cloud_scheduler.cron,
            "time_zone": resource.cloud_scheduler.timezone,
            # TODO: "retry_config" ,
            # TODO: "attempt_deadline"
        }

        try:
            _ = client.get_job({"name": job_name})
            logger.user_info(f"Found {job_name} cloud scheduler job, updating it")
            client.update_job(
                {
                    "job": job,
                    "update_mask": {"paths": ["schedule", "http_target", "time_zone"]},
                }
            )

        except NotFound:
            # Does not exist let's create it
            logger.user_info(
                f"Creating {job_name} with deployment manifest for {env} with version {version}"
            )
            client.create_job({"parent": parent, "job": job})

        logging_metric_ref = f"{job_id}-cloud-scheduler-errors"
        gcp_resource_type = "cloud_scheduler_job"
        self.upsert_log_metric(
            LogMetricResource(
                project=resource.project,
                location=resource.location,
                name=logging_metric_ref,
                filter_=f"""
            resource.type="{gcp_resource_type}" AND severity >= WARNING AND resource.labels.job_id="{job_id}"
            """,
                description=f"Log metric for {resource.name} cloud scheduler job",
            )
        )

        self.upsert_alert_policy(
            AlertPolicyResource(
                logging_metric_type=logging_metric_ref,
                resource_type=gcp_resource_type,
                project=resource.project,
                location=resource.location,
                name=f"{job_id}-cloud-scheduler-alert-policy",
                display_name=f"{job_id}-cloud-scheduler-alert-policy",
                labels=resource.labels,
                notification_channels=resource.notification_channels,
            )
        )

    def upsert_cloud_function(
        self, resource: CloudFunctionResource, version: str, env: str
    ) -> Tuple[str, str]:
        logger.user_info(
            f"Deploying {resource.name} cloud function with version {version} to env {env}"
        )
        parent = f"projects/{resource.project}/locations/{resource.location}"
        pipeline_functions_dir = resource.build_dir / "functions"
        os.makedirs(pipeline_functions_dir, exist_ok=True)
        local_functions_package = pipeline_functions_dir / "package.zip"
        functions_gcs_path_dir = f"{resource.resource_root}/functions"
        functions_gcs_path = f"{functions_gcs_path_dir}/package.zip"
        function_name = f"{resource.name}-{env}"
        function_path = f"{parent}/functions/{function_name}"

        cloud_function = templates.render_template(
            Path("scheduler_cloud_function.py"),
            manifest=resource.template_vars,
            labels=json.dumps(resource.labels, separators=(",", ":")),
        )

        requirements = templates.render_template(
            Path("scheduler_cloud_function_requirements.txt"),
            manifest=resource.template_vars,
        )

        with zipfile.ZipFile(local_functions_package, "w") as z:
            z.writestr("main.py", cloud_function)
            z.writestr("requirements.txt", requirements)

        if not is_gcs_path(functions_gcs_path_dir):
            os.makedirs(functions_gcs_path_dir, exist_ok=True)

        self.upload_file(str(local_functions_package), functions_gcs_path)

        cf = CloudFunctionsServiceClient(credentials=self.credentials)
        function_url = f"https://{resource.location}-{resource.project}.cloudfunctions.net/{function_name}"
        function = {
            "name": function_path,
            "description": f"wanna {resource.name} function for {env} pipeline",
            "source_archive_url": functions_gcs_path,
            "entry_point": "process_request",
            "runtime": "python39",
            "https_trigger": {
                "url": function_url,
            },
            "service_account_email": resource.service_account,
            "labels": resource.labels,
            "environment_variables": {
                snakecase(k).upper(): v for k, v in resource.env_params.items()
            }
            # TODO: timeout
        }

        try:
            cf.get_function({"name": function_path})
            cf.update_function({"function": function}).result()
        # it can raise denied on resource 'projects/{project_id}/locations/{loaction}/functions/{function_name}'
        # (or resource may not exist).
        except (NotFound, PermissionDenied):
            cf.create_function({"location": parent, "function": function}).result()

        logging_metric_ref = f"{function_name}-cloud-function-errors"
        gcp_resource_type = "cloud_function"
        self.upsert_log_metric(
            LogMetricResource(
                name=logging_metric_ref,
                project=resource.project,
                location=resource.location,
                filter_=f"""
                resource.type="{gcp_resource_type}" AND severity >= WARNING
                AND resource.labels.function_name="{function_name}"
                """,
                description=f"Log metric for {function_name} cloud function executions",
            )
        )

        self.upsert_alert_policy(
            AlertPolicyResource(
                name=f"{function_name}-cloud-function-alert-policy",
                project=resource.project,
                location=resource.location,
                logging_metric_type=logging_metric_ref,
                resource_type=gcp_resource_type,
                display_name=f"{function_name}-cloud-function-alert-policy",
                labels=resource.labels,
                notification_channels=resource.notification_channels,
            )
        )

        return (
            function_path,
            function_url,
        )
