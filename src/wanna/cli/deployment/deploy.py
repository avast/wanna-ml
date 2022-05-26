import json
import os
import zipfile
from pathlib import Path
from typing import Tuple

from google.api_core.exceptions import NotFound
from google.cloud import scheduler_v1
from google.cloud.functions_v1 import CloudFunctionsServiceClient
from smart_open import open

from wanna.cli.deployment.models import CloudFunctionResource, CloudSchedulerResource
from wanna.cli.utils import templates
from wanna.cli.utils.gcp.gcp import is_gcs_path
from wanna.cli.utils.spinners import Spinner


def _sync_cloud_function_package(local_functions_package: str, functions_gcs_path: str):
    with open(local_functions_package, "rb") as f:
        with open(functions_gcs_path, "wb") as fout:
            fout.write(f.read())


def upsert_cloud_function(resource: CloudFunctionResource, version: str, env: str, spinner: Spinner) -> Tuple[str, str]:

    spinner.info(f"Deploying {resource.name} cloud function with version {version} to env {env}")
    parent = f"projects/{resource.project}/locations/{resource.location}"
    pipeline_functions_dir = resource.build_dir / resource.name / "functions"
    os.makedirs(pipeline_functions_dir, exist_ok=True)
    local_functions_package = pipeline_functions_dir / "package.zip"
    functions_gcs_path_dir = f"{resource.resource_root}/deployment/release/{version}/functions"
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

    cf = CloudFunctionsServiceClient()
    function_url = f"https://{resource.project}-{resource.location}.cloudfunctions.net/{function_name}"
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
        # TODO: timeout
        # TODO: environment_variables
    }

    try:
        cf.get_function({"name": function_path})
        cf.update_function({"function": function}).result()
        return (
            function_path,
            function_url,
        )
    except NotFound:
        cf.create_function({"location": parent, "function": function}).result()
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
    client = scheduler_v1.CloudSchedulerClient()
    parent = f"projects/{resource.project}/locations/{resource.location}"
    job_name = f"{parent}/jobs/{resource.name}-{env}"
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
        # TODO: "retry_config"
        # "attempt_deadline"
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
