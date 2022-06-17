import atexit
from pathlib import Path
from typing import Optional

from google.cloud.aiplatform import PipelineJob
from google.cloud.aiplatform.compat.types import pipeline_state_v1 as gca_pipeline_state_v1

from wanna.core.deployment.artifacts_push import ArtifactsPushMixin
from wanna.core.deployment.models import (
    CloudFunctionResource,
    CloudSchedulerResource,
    NotificationChannelResource,
    PipelineResource,
)
from wanna.core.deployment.vertex_scheduling import VertexSchedulingMixIn
from wanna.core.loggers.wanna_logger import get_logger
from wanna.core.services.path_utils import PipelinePaths
from wanna.core.utils.gcp import convert_project_id_to_project_number
from wanna.core.utils.loaders import load_yaml_path
from wanna.core.utils.time import get_timestamp

logger = get_logger(__name__)


class VertexPipelinesMixInVertex(VertexSchedulingMixIn, ArtifactsPushMixin):
    @staticmethod
    def _at_pipeline_exit(pipeline_name: str, pipeline_job: PipelineJob, sync: bool) -> None:
        @atexit.register
        def stop_pipeline_job():
            if sync and pipeline_job and getattr(pipeline_job._gca_resource, "name", None):
                if pipeline_job.state != gca_pipeline_state_v1.PipelineState.PIPELINE_STATE_SUCCEEDED:
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
        override_params = load_yaml_path(extra_params, Path(".")) if extra_params else {}
        pipeline_params = {**resource.parameter_values, **override_params}

        project_number = convert_project_id_to_project_number(resource.project)
        network = f"projects/{project_number}/global/networks/{resource.network}"

        # Define Vertex AI Pipeline job
        pipeline_job = PipelineJob(
            display_name=resource.pipeline_name,
            job_id=pipeline_job_id,
            template_path=str(resource.json_spec_path),
            pipeline_root=resource.pipeline_root,
            parameter_values=pipeline_params,
            enable_caching=True,
            labels=resource.labels,
            project=resource.project,
            location=resource.location,
        )

        VertexPipelinesMixInVertex._at_pipeline_exit(resource.pipeline_name, pipeline_job, sync)

        # submit pipeline job for execution
        pipeline_job.submit(service_account=resource.service_account, network=network)

        if sync:
            logger.user_info(f"Pipeline dashboard at {pipeline_job._dashboard_uri()}.")
            pipeline_job.wait()

    def deploy_pipeline(
        self, resource: PipelineResource, pipeline_paths: PipelinePaths, version: str, env: str
    ) -> None:

        base_resource = {
            "project": resource.project,
            "location": resource.location,
            "service_account": (
                resource.schedule.service_account
                if resource.schedule and resource.schedule.service_account
                else resource.service_account
            ),
        }

        # Create notification channels
        channels = []
        for config in resource.notification_channels:
            for email in config.emails:
                channel_config = {"email_address": email}
                name = email.split("@")[0].replace(".", "-")
                channel = self.upsert_notification_channel(
                    resource=NotificationChannelResource(
                        type_=config.type,
                        name=f"{name}-wanna-email-channel",
                        config=channel_config,
                        labels=resource.labels,
                        **base_resource,
                    )
                )
                channels.append(channel.name)

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
            logger.user_info("Deployment Manifest does not have a schedule set. Skipping Cloud Scheduler sync")

        # not possible to set alerts for failed PipelineJobs
        # since aiplatform.googleapis.com/PipelineJob
        # is not a monitored job
        # https://cloud.google.com/monitoring/api/resources
        # logging_metric_ref = f"{manifest.pipeline_name}-ml-pipeline-error"
        # gcp_resource_type = "aiplatform.googleapis.com/PipelineJob"
        # deploy.upsert_log_metric(LogMetricResource(
        #     project=manifest.project,
        #     name=logging_metric_ref,
        #     filter_= f"""
        #     resource.type="{gcp_resource_type}"
        #     AND severity >= WARNING
        #     AND resource.labels.pipeline_job_id:"{manifest.pipeline_name}"
        #     """,
        #     description=f"Log metric for {manifest.pipeline_name} vertex ai pipeline"
        # ))
        # deploy.upsert_alert_policy(
        #     logging_metric_type=logging_metric_ref,
        #     resource_type=gcp_resource_type,
        #     project=manifest.project,
        #     name=f"{manifest.pipeline_name}-ml-pipeline-alert-policy",
        #     display_name=f"{logging_metric_ref}-ml-pipeline-alert-policy",
        #     labels=manifest.labels,
        #     notification_channels=["projects/cloud-lab-304213/notificationChannels/1568320106180659521"]
        # )
