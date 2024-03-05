import atexit
import json
import os
import zipfile
from pathlib import Path
from typing import Optional

from google.api_core.exceptions import AlreadyExists
from google.cloud import logging
from google.cloud.aiplatform import PipelineJob
from google.cloud.aiplatform.compat.types import (
    pipeline_state_v1 as gca_pipeline_state_v1,
)
from google.cloud.functions_v1 import CloudFunctionsServiceClient

from wanna.core.deployment.artifacts_push import ArtifactsPushMixin
from wanna.core.deployment.models import (
    AlertPolicyResource,
    CloudFunctionResource,
    CloudSchedulerResource,
    LogMetricResource,
    NotificationChannelResource,
    PipelineResource,
)
from wanna.core.deployment.vertex_scheduling import VertexSchedulingMixIn
from wanna.core.loggers.wanna_logger import get_logger
from wanna.core.models.notification_channel import (
    EmailNotificationChannel,
    PubSubNotificationChannel,
)
from wanna.core.services.path_utils import PipelinePaths
from wanna.core.utils import templates
from wanna.core.utils.gcp import is_gcs_path
from wanna.core.utils.loaders import load_yaml_path
from wanna.core.utils.time import get_timestamp, update_time_template

logger = get_logger(__name__)


class VertexPipelinesMixInVertex(VertexSchedulingMixIn, ArtifactsPushMixin):
    @staticmethod
    def _at_pipeline_exit(
        pipeline_name: str, pipeline_job: PipelineJob, sync: bool
    ) -> None:
        @atexit.register
        def stop_pipeline_job():
            if (
                sync
                and pipeline_job
                and getattr(pipeline_job._gca_resource, "name", None)
            ):
                if (
                    pipeline_job.state
                    != gca_pipeline_state_v1.PipelineState.PIPELINE_STATE_SUCCEEDED
                ):
                    logger.user_error(
                        "detected exit signal, "
                        f"shutting down running pipeline {pipeline_name} "
                        f"at {pipeline_job._dashboard_uri()}."
                    )
                    pipeline_job.wait()
                    pipeline_job.cancel()

    def run_pipeline(
        self,
        resource: PipelineResource,
        extra_params: Optional[Path],
        sync: bool = True,
    ) -> None:
        mode = "sync mode" if sync else "fire-forget mode"

        logger.user_info(f"Running pipeline {resource.pipeline_name} in {mode}")

        # fetch compiled params
        pipeline_job_id = f"pipeline-{resource.pipeline_name}-{get_timestamp()}"

        # Apply override with cli provided params file
        override_params = (
            load_yaml_path(extra_params, Path(".")) if extra_params else {}
        )
        pipeline_params = {**resource.parameter_values, **override_params}
        pipeline_params = update_time_template(pipeline_params)

        # Define Vertex AI Pipeline job
        pipeline_job = PipelineJob(
            display_name=resource.pipeline_name,
            job_id=pipeline_job_id,
            template_path=str(resource.json_spec_path),
            pipeline_root=resource.pipeline_root,
            parameter_values=pipeline_params,
            enable_caching=resource.enable_caching,
            labels=resource.labels,
            project=resource.project,
            location=resource.location,
            encryption_spec_key_name=resource.encryption_spec_key_name,
        )

        VertexPipelinesMixInVertex._at_pipeline_exit(
            resource.pipeline_name, pipeline_job, sync
        )

        # submit pipeline job for execution
        experiment = (
            resource.experiment
            if resource.experiment
            else f"{resource.pipeline_name}-experiment"
        )

        pipeline_job.submit(
            service_account=resource.service_account,
            network=resource.network,
            experiment=experiment,
        )

        if sync:
            logger.user_info(f"Pipeline dashboard at {pipeline_job._dashboard_uri()}.")
            pipeline_job.wait()

    def deploy_pipeline(
        self,
        resource: PipelineResource,
        pipeline_paths: PipelinePaths,
        version: str,
        env: str,
    ) -> None:
        pipeline_service_account = (
            resource.schedule.service_account
            if resource.schedule and resource.schedule.service_account
            else resource.service_account
        )

        base_resource = {
            "project": resource.project,
            "location": resource.location,
            "service_account": str(pipeline_service_account),
        }

        # Create notification channels
        channels = []
        for config in resource.notification_channels:
            if isinstance(config, EmailNotificationChannel):
                for email in config.emails:
                    channel_config = {"email_address": str(email)}
                    name = email.split("@")[0].replace(".", "-")
                    channel = self.upsert_notification_channel(
                        resource=NotificationChannelResource(
                            type_=config.type,
                            description=config.description,
                            name=f"{name}-wanna-email-channel",
                            config=channel_config,
                            labels=resource.labels,
                            **base_resource,
                        )
                    )
                    channels.append(channel.name)
            elif isinstance(config, PubSubNotificationChannel):
                for topic in config.topics:
                    project_id = resource.compile_env_params.get("project_id")
                    channel_config = {"topic": f"projects/{project_id}/topics/{topic}"}
                    channel = self.upsert_notification_channel(
                        resource=NotificationChannelResource(
                            type_=config.type,
                            description=config.description,
                            name=f"{topic}-wanna-alert-topic-channel",
                            config=channel_config,
                            labels=resource.labels,
                            **base_resource,
                        )
                    )
                    channels.append(channel.name)
            else:
                raise ValueError(
                    f"Validation error notification config {config} can't be handled by wanna-ml"
                )

        function = self.upsert_cloud_function(
            resource=CloudFunctionResource(
                name=resource.pipeline_name,
                build_dir=pipeline_paths.get_local_pipeline_deployment_path(version),
                resource_root=pipeline_paths.get_gcs_pipeline_deployment_path(version),
                resource_function_template="scheduler_cloud_function.py",
                resource_requirements_template="scheduler_cloud_function_requirements.txt",
                template_vars=resource.dict(),
                env_params=resource.compile_env_params,
                labels=resource.labels,
                network=resource.network,
                notification_channels=channels,
                **base_resource,
            ),
            env=env,
            version=version,
        )

        if resource.schedule:
            pipeline_spec_path = pipeline_paths.get_gcs_pipeline_json_spec_path(version)
            body = {
                "pipeline_spec_uri": pipeline_spec_path,
                "parameter_values": resource.parameter_values,
                "enable_caching": resource.enable_caching,
            }  # TODO extend with execution_date(now) ?

            self.upsert_cloud_scheduler(
                function=function,
                resource=CloudSchedulerResource(
                    name=resource.pipeline_name,
                    body=body,
                    cloud_scheduler=resource.schedule,
                    labels=resource.labels,
                    notification_channels=channels,
                    **base_resource,
                ),
                env=env,
                version=version,
            )

        else:
            logger.user_info(
                "Deployment Manifest does not have a schedule set. Skipping Cloud Scheduler sync"
            )

        logging_metric_ref = f"{resource.pipeline_name}-ml-pipeline-error"
        gcp_resource_type = "aiplatform.googleapis.com/PipelineJob"
        self.upsert_log_metric(
            LogMetricResource(
                project=resource.project,
                name=logging_metric_ref,
                location=resource.location,
                filter_=f"""
            resource.type="{gcp_resource_type}"
            AND severity >= WARNING
            AND resource.labels.pipeline_job_id:"{resource.pipeline_name}"
            """,
                description=f"Log metric for {resource.pipeline_name} vertex ai pipeline",
            )
        )
        logging_policy_name = f"{resource.pipeline_name}-{env}-ml-pipeline-alert-policy"
        self.upsert_alert_policy(
            AlertPolicyResource(
                name=logging_policy_name,
                project=resource.project,
                location=resource.location,
                logging_metric_type=logging_metric_ref,
                resource_type=gcp_resource_type,
                display_name=logging_policy_name,
                labels=resource.labels,
                notification_channels=channels,
            )
        )

        if "wanna_sla_hours" in resource.labels:
            self.upsert_sink(resource)
            self.upsert_sla_function(resource, version, env)

    def upsert_sink(self, resource: PipelineResource):
        """Creates a sink to export logs to the given Cloud Storage bucket.
        The filter determines which logs this sink matches and will be exported
        to the destination.
        """
        logging_client = logging.Client()

        destination = "storage.googleapis.com/" + f"{resource.pipeline_bucket}"[5:]
        filter_ = f"""resource.type="aiplatform.googleapis.com/PipelineJob"
        AND jsonPayload.pipelineName="{resource.pipeline_name}"
        AND jsonPayload.state="PIPELINE_STATE_RUNNING"
        """
        sink_name = f"{resource.pipeline_name}-sink-{resource.pipeline_version}"

        sink = logging_client.sink(sink_name, filter_=filter_, destination=destination)

        if sink.exists():
            logger.user_error("Sink {} already exists.".format(sink.name))
            return

        sink.create()
        logger.user_info("Created sink {}".format(sink.name))

    def upsert_sla_function(
        self, resource: PipelineResource, version: str, env: str
    ) -> None:
        logger.user_info(
            f"Deploying {resource.pipeline_name} SLA monitoring function with version {version} to env {env}"
        )
        parent = f"projects/{resource.project}/locations/{resource.location}"
        local_functions_package = "sla.zip"
        functions_gcs_path_dir = f"{resource.pipeline_bucket}/wanna-pipelines/{resource.pipeline_name}/deployment/{version}/functions"
        functions_gcs_path = f"{functions_gcs_path_dir}/sla.zip"
        function_name = f"{resource.pipeline_name}-{env}-{version}"
        function_path = f"{parent}/functions/{function_name}"

        cloud_function = templates.render_template(
            Path("sla_cloud_function.py"),
            labels=json.dumps(resource.labels, separators=(",", ":")),
        )

        requirements = templates.render_template(
            Path("sla_cloud_function_requirements.txt")
        )

        with zipfile.ZipFile(local_functions_package, "w") as z:
            z.writestr("main.py", cloud_function)
            z.writestr("requirements.txt", requirements)

        if not is_gcs_path(functions_gcs_path_dir):
            os.makedirs(functions_gcs_path_dir, exist_ok=True)

        self.upload_file(str(local_functions_package), functions_gcs_path)

        cf = CloudFunctionsServiceClient(credentials=self.credentials)

        function = {
            "name": function_path,
            "description": f"wanna {resource.pipeline_name} function for {env} pipeline",
            "source_archive_url": functions_gcs_path,
            "entry_point": "main",
            "runtime": "python39",
            "event_trigger": {
                "event_type": "google.storage.object.finalize",
                "resource": f"projects/{resource.project}/buckets/"
                + f"{resource.pipeline_bucket}"[5:],
            },
            "service_account_email": resource.service_account,
            "labels": resource.labels,
        }
        try:
            cf.create_function({"location": parent, "function": function}).result()
        except AlreadyExists:
            logger.user_error(
                f"Function {function_name} already exists, no need to re-deploy"
            )
