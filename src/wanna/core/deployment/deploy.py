import json
import os
import zipfile
from pathlib import Path
from typing import Tuple, cast

import google.cloud.logging
from caseconverter import snakecase
from google.api_core.exceptions import NotFound, PermissionDenied
from google.cloud import scheduler_v1
from google.cloud.functions_v1 import CloudFunctionsServiceClient
from google.cloud.monitoring_v3 import AlertPolicy
from google.cloud.monitoring_v3.services.alert_policy_service import AlertPolicyServiceClient

from wanna.core.deployment.models import (
    AlertPolicyResource,
    CloudFunctionResource,
    CloudSchedulerResource,
    LogMetricResource,
)
from wanna.core.utils import templates
from wanna.core.utils.credentials import get_credentials
from wanna.core.utils.gcp import is_gcs_path
from wanna.core.utils.io import open
from wanna.core.utils.spinners import Spinner


def _sync_cloud_function_package(local_functions_package: str, functions_gcs_path: str):
    with open(local_functions_package, "rb") as f:
        with open(functions_gcs_path, "wb") as fout:
            fout.write(f.read())


def upsert_cloud_function(resource: CloudFunctionResource, version: str, env: str, spinner: Spinner) -> Tuple[str, str]:

    spinner.info(f"Deploying {resource.name} cloud function with version {version} to env {env}")
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
        Path("scheduler_cloud_function_requirements.txt"), manifest=resource.template_vars
    )

    with zipfile.ZipFile(local_functions_package, "w") as z:
        z.writestr("main.py", cloud_function)
        z.writestr("requirements.txt", requirements)

    if not is_gcs_path(functions_gcs_path_dir):
        os.makedirs(functions_gcs_path_dir, exist_ok=True)

    _sync_cloud_function_package(str(local_functions_package), functions_gcs_path)

    cf = CloudFunctionsServiceClient(credentials=get_credentials())
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
        "environment_variables": {snakecase(k).upper(): v for k, v in resource.env_params.items()}
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
    upsert_log_metric(
        LogMetricResource(
            project=resource.project,
            name=logging_metric_ref,
            filter_=f"""
            resource.type="{gcp_resource_type}" AND severity >= WARNING
            AND resource.labels.function_name="{function_name}"
            """,
            description=f"Log metric for {function_name} cloud function executions",
        )
    )
    upsert_alert_policy(
        AlertPolicyResource(
            logging_metric_type=logging_metric_ref,
            resource_type=gcp_resource_type,
            project=resource.project,
            name=f"{function_name}-cloud-function-alert-policy",
            display_name=f"{function_name}-cloud-function-alert-policy",
            labels=resource.labels,
            notification_channels=["projects/cloud-lab-304213/notificationChannels/1568320106180659521"],
        )
    )

    return (
        function_path,
        function_url,
    )


def upsert_cloud_scheduler(
    function: Tuple[str, str],
    resource: CloudSchedulerResource,
    version: str,
    env: str,
    spinner: Spinner,
) -> None:
    client = scheduler_v1.CloudSchedulerClient(credentials=get_credentials())
    parent = f"projects/{resource.project}/locations/{resource.location}"
    job_id = f"{resource.name}-{env}"
    job_name = f"{parent}/jobs/{job_id}"
    function_name, function_url = function

    spinner.info(f"Deploying {resource.name} cloud scheduler with version {version} to env {env}")

    http_target = {
        "uri": function_url,
        "body": json.dumps(resource.body, separators=(",", ":")).encode(),
        "headers": {
            "Content-Type": "application/octet-stream",
            "User-Agent": "Google-Cloud-Scheduler",
            "Wanna-Pipeline-Version": version,
        },
        "oidc_token": {
            "service_account_email": resource.cloud_scheduler.service_account or resource.service_account,
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
        job = client.get_job({"name": job_name})
        spinner.info(f"Found {job.name} cloud scheduler job")
        spinner.info(f"Updating {job.name} cloud scheduler job")
        client.update_job({"job": job})
    except NotFound:
        # Does not exist let's create it
        spinner.info(f"Creating {job_name} with deployment manifest for {env} with version {version}")
        client.create_job({"parent": parent, "job": job})

    logging_metric_ref = f"{job_id}-cloud-scheduler-errors"
    gcp_resource_type = "cloud_scheduler_job"
    upsert_log_metric(
        LogMetricResource(
            project=resource.project,
            name=logging_metric_ref,
            filter_=f"""
        resource.type="{gcp_resource_type}" AND severity >= WARNING AND resource.labels.job_id="{job_id}"
        """,
            description=f"Log metric for {resource.name} cloud scheduler job",
        )
    )
    upsert_alert_policy(
        AlertPolicyResource(
            logging_metric_type=logging_metric_ref,
            resource_type=gcp_resource_type,
            project=resource.project,
            name=f"{job_id}-cloud-scheduler-alert-policy",
            display_name=f"{job_id}-cloud-scheduler-alert-policy",
            labels=resource.labels,
            notification_channels=["projects/cloud-lab-304213/notificationChannels/1568320106180659521"],
        )
    )


def upsert_alert_policy(resource: AlertPolicyResource):
    client = AlertPolicyServiceClient(credentials=get_credentials())
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
                    "threshold_value": 1,
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


def upsert_log_metric(resource: LogMetricResource):
    client = google.cloud.logging.Client(credentials=get_credentials())
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
