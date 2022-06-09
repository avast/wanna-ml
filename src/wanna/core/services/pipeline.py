import json
import os
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import pandas as pd
from caseconverter import snakecase
from google.cloud import aiplatform
from google.cloud.aiplatform.pipeline_jobs import PipelineJob
from kfp.v2.compiler.main import compile_pyfile
from python_on_whales import Image

from wanna.core.deployment import deploy
from wanna.core.deployment.models import (
    CloudFunctionResource,
    CloudSchedulerResource,
    ContainerArtifact,
    JsonArtifact,
    PathArtifact,
    PushMode,
    PushTask, LogMetricResource,
)
from wanna.core.deployment.push import PushResult, push
from wanna.core.models.docker import DockerBuildResult, DockerImageModel, ImageBuildType
from wanna.core.models.pipeline import PipelineDeployment, PipelineModel
from wanna.core.models.wanna_config import WannaConfigModel
from wanna.core.services.base import BaseService
from wanna.core.services.docker import DockerService
from wanna.core.services.pipeline_utils import PipelinePaths, _at_pipeline_exit
from wanna.core.services.tensorboard import TensorboardService
from wanna.core.utils.gcp import convert_project_id_to_project_number
from wanna.core.utils.io import open
from wanna.core.utils.loaders import load_yaml_path
from wanna.core.utils.spinners import Spinner
from wanna.core.utils.time import get_timestamp


class PipelineService(BaseService[PipelineModel]):
    def __init__(
        self,
        config: WannaConfigModel,
        workdir: Path,
        version: str = "dev",
        push_mode: PushMode = PushMode.all,
    ):
        super().__init__(
            instance_type="pipeline",
        )
        self.instances = config.pipelines
        self.config = config
        self.workdir = workdir
        self.tensorboard_service = TensorboardService(config=config)
        self.version = version
        self.push_mode = push_mode
        self.docker_service = DockerService(
            docker_model=config.docker,  # type: ignore
            gcp_profile=config.gcp_profile,
            version=version,
            work_dir=workdir,
            wanna_project_name=self.config.wanna_project.name,
            quick_mode=push_mode.is_quick_mode(),
        )

    def build(self, instance_name: str) -> List[Path]:
        """
        Create an instance with name "name" based on wanna-ml config.
        Args:
            instance_name: The name of the only instance from wanna-ml config that should be created.
                  Set to "all" to create everything from wanna-ml yaml configuration.
        """
        instances = self._filter_instances_by_name(instance_name)
        return [self._compile_one_instance(instance) for instance in instances]

    def push(self, manifests: List[Path], local: bool = False) -> PushResult:
        return push(self.docker_service, self._prepare_push(manifests, self.version, local))

    def _prepare_push(self, pipelines: List[Path], version: str, local: bool = False) -> List[PushTask]:
        push_tasks = []
        for local_manifest_path in pipelines:
            manifest = PipelineService.read_manifest(str(local_manifest_path))
            pipeline_paths = PipelinePaths(self.workdir, manifest.pipeline_bucket, manifest.pipeline_name)
            json_artifacts, manifest_artifacts, container_artifacts = [], [], []

            with Spinner(text=f"Packaging {manifest.pipeline_name} pipeline resources"):

                # Push containers if we are running on Internal Teamcity build agent or on local(all)
                if self.push_mode.can_push_containers():
                    for ref in manifest.docker_refs:
                        if ref.build_type != ImageBuildType.provided_image:
                            container_artifacts.append(ContainerArtifact(title=ref.name, tags=ref.tags))

                # Push gcp resources if we are running on GCP build agent
                if self.push_mode.can_push_gcp_resources():

                    # Prepare manifest paths
                    local_kubeflow_json_spec_path = pipeline_paths.get_local_pipeline_json_spec_path(version)
                    wanna_manifest_publish_path = pipeline_paths.get_gcs_wanna_manifest_path(version)
                    kubeflow_json_spec_publish_path = pipeline_paths.get_gcs_pipeline_json_spec_path(version)

                    if local:
                        # Override paths to local dir when in "local" mode, IE tests or local run
                        wanna_manifest_publish_path = pipeline_paths.get_local_wanna_manifest_path(version)
                        kubeflow_json_spec_publish_path = pipeline_paths.get_local_pipeline_json_spec_path(version)

                    # Ensure to update manifest json_spec_path to have the actual gcs location
                    manifest.json_spec_path = kubeflow_json_spec_publish_path

                    json_artifacts.append(
                        JsonArtifact(
                            title="WANNA pipeline manifest",
                            json_body=manifest.dict(),
                            destination=wanna_manifest_publish_path,
                        )
                    )

                    manifest_artifacts.append(
                        PathArtifact(
                            title="Kubeflow V2 pipeline spec",
                            source=local_kubeflow_json_spec_path,
                            destination=manifest.json_spec_path,
                        )
                    )

                push_tasks.append(
                    PushTask(
                        manifest_artifacts=manifest_artifacts,
                        container_artifacts=container_artifacts,
                        json_artifacts=json_artifacts,
                    )
                )

        return push_tasks

    def deploy(self, instance_name: str, env: str):

        instances = self._filter_instances_by_name(instance_name)
        for pipeline in instances:
            with Spinner(text=f"Deploying {pipeline.name} version {self.version} to env {env}") as s:
                pipeline_paths = PipelinePaths(
                    self.workdir,
                    pipeline.bucket or f"gs://{self.config.gcp_profile.bucket}",
                    pipeline_name=pipeline.name,
                )
                manifest = PipelineService.read_manifest(pipeline_paths.get_gcs_wanna_manifest_path(self.version))

                function = deploy.upsert_cloud_function(
                    resource=CloudFunctionResource(
                        name=manifest.pipeline_name,
                        project=manifest.project,
                        location=manifest.location,
                        service_account=manifest.schedule.service_account
                        if manifest.schedule and manifest.schedule.service_account
                        else manifest.service_account,
                        build_dir=pipeline_paths.get_local_pipeline_deployment_path(self.version),
                        resource_root=pipeline_paths.get_gcs_pipeline_deployment_path(self.version),
                        resource_function_template="scheduler_cloud_function.py",
                        resource_requirements_template="scheduler_cloud_function_requirements.txt",
                        template_vars=manifest.dict(),
                        env_params=manifest.compile_env_params,
                        labels=manifest.labels,
                        network=manifest.network,
                    ),
                    env=env,
                    version=self.version,
                    spinner=s,
                )

                if manifest.schedule:
                    pipeline_spec_path = pipeline_paths.get_gcs_pipeline_json_spec_path(self.version)
                    body = {
                        "pipeline_spec_uri": pipeline_spec_path,
                        "parameter_values": manifest.parameter_values,
                    }  # TODO extend with execution_date(now) ?

                    deploy.upsert_cloud_scheduler(
                        function=function,
                        resource=CloudSchedulerResource(
                            name=manifest.pipeline_name,
                            project=manifest.project,
                            location=manifest.location,
                            body=body,
                            cloud_scheduler=manifest.schedule,
                            service_account=manifest.service_account,
                            labels=manifest.labels
                        ),
                        env=env,
                        version=self.version,
                        spinner=s,
                    )

                else:
                    s.info("Deployment Manifest does not have a schedule set. Skipping Cloud Scheduler sync")

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

    @staticmethod
    def run(
        pipelines: List[str],
        extra_params_path: Optional[Path] = None,
        sync: bool = True,
        service_account: Optional[str] = None,
        network: Optional[str] = None,
        exit_callback: Callable[[str, PipelineJob, bool, Spinner], None] = _at_pipeline_exit,
    ) -> None:

        for manifest_path in pipelines:

            manifest = PipelineService.read_manifest(str(manifest_path))

            aiplatform.init(location=manifest.location, project=manifest.project)

            mode = "sync mode" if sync else "fire-forget mode"

            with Spinner(text=f"Running pipeline {manifest.pipeline_name} in {mode}") as s:

                # fetch compiled params
                pipeline_job_id = f"pipeline-{manifest.pipeline_name}-{get_timestamp()}"

                # Apply override with cli provided params file
                override_params = load_yaml_path(extra_params_path, Path(".")) if extra_params_path else {}
                pipeline_params = {**manifest.parameter_values, **override_params}

                # Select service account for pipeline job
                service_account = service_account or manifest.service_account

                network = network if network else manifest.network
                project_number = convert_project_id_to_project_number(manifest.project)
                network = f"projects/{project_number}/global/networks/{network}"

                # Define Vertex AI Pipeline job
                pipeline_job = PipelineJob(
                    display_name=manifest.pipeline_name,
                    job_id=pipeline_job_id,
                    template_path=str(manifest.json_spec_path),
                    pipeline_root=manifest.pipeline_root,
                    parameter_values=pipeline_params,
                    enable_caching=True,
                    labels=manifest.labels,
                    project=manifest.project,
                    location=manifest.location,
                )

                # Cancel pipeline if wanna process exits
                exit_callback(manifest.pipeline_name, pipeline_job, sync, s)

                # submit pipeline job for execution
                # TODO: should we remove service_account and  network from this call ?
                pipeline_job.submit(service_account=service_account, network=network)

                if sync:
                    s.info(f"Pipeline dashboard at {pipeline_job._dashboard_uri()}.")
                    pipeline_job.wait()

                    df_pipeline = aiplatform.get_pipeline_df(pipeline=manifest.pipeline_name.replace("_", "-"))
                    with pd.option_context(
                        "display.max_rows", None, "display.max_columns", None
                    ):  # more options can be specified also
                        s.info(f"Pipeline results info: \n\t{df_pipeline}")

    def _export_pipeline_params(
        self,
        pipeline_paths: PipelinePaths,
        pipeline_instance: PipelineModel,
        version: str,
        images: List[Tuple[DockerImageModel, Optional[Image], str]],
        tensorboard: Optional[str],
        network = str,
    ):

        labels = {"wanna_pipeline": pipeline_instance.name}
        if pipeline_instance.labels:
            labels = {**pipeline_instance.labels, **labels}

        # Prepare env params to be exported
        pipeline_env_params = {
            "project_id": pipeline_instance.project_id,
            "pipeline_name": pipeline_instance.name,
            "version": version,
            "bucket": pipeline_instance.bucket,
            "region": pipeline_instance.region,
            "pipeline_root": pipeline_paths.get_gcs_pipeline_root(),
            "pipeline_labels": json.dumps(labels),
            "pipeline_network": network,
            "pipeline_service_account": (
                pipeline_instance.service_account
                if pipeline_instance.service_account
                else self.config.gcp_profile.service_account
            ),
        }

        if tensorboard:
            pipeline_env_params["tensorboard"] = tensorboard

        # Export Pipeline wanna ENV params to be available during compilation
        pipeline_name_prefix = snakecase(f"{pipeline_instance.name}").upper()
        for key, value in pipeline_env_params.items():
            env_name = snakecase(f"{pipeline_name_prefix}_{key.upper()}").upper()
            os.environ[env_name] = value

        for (docker_image_model, _, tag) in images:
            env_name = snakecase(f"{docker_image_model.name}_DOCKER_URI").upper()
            os.environ[env_name] = tag

        # Collect pipeline compile params from wanna config
        if pipeline_instance.pipeline_params and isinstance(pipeline_instance.pipeline_params, Path):
            pipeline_params_path = (self.workdir / pipeline_instance.pipeline_params).resolve()
            pipeline_compile_params = load_yaml_path(pipeline_params_path, self.workdir)
        elif pipeline_instance.pipeline_params and isinstance(pipeline_instance.pipeline_params, dict):
            pipeline_compile_params = pipeline_instance.pipeline_params
        else:
            pipeline_compile_params = {}

        return pipeline_env_params, pipeline_compile_params

    def _compile_one_instance(self, pipeline: PipelineModel) -> Path:

        image_tags = [
            self.docker_service.get_image(docker_image_ref=docker_image_ref)
            for docker_image_ref in pipeline.docker_image_ref
        ]

        Spinner().info(text=f"Compiling pipeline {pipeline.name}")

        # Prep build dir
        pipeline_paths = PipelinePaths(
            self.workdir, pipeline.bucket or f"gs://{self.config.gcp_profile.bucket}", pipeline.name
        )
        tensorboard = (
            self.tensorboard_service.get_or_create_tensorboard_instance_by_name(pipeline.tensorboard_ref)
            if pipeline.tensorboard_ref and self.push_mode.can_push_gcp_resources()
            else None
        )

        pipeline_network = pipeline.network if pipeline.network else self.config.gcp_profile.network
        project_number = convert_project_id_to_project_number(pipeline.project_id)
        network = f"projects/{project_number}/global/networks/{pipeline_network}"

        # Collect kubeflow pipeline params for compilation
        pipeline_env_params, pipeline_params = self._export_pipeline_params(
            pipeline_paths, pipeline, self.version, image_tags, tensorboard, network
        )

        # Compile kubeflow V2 Pipeline
        compile_pyfile(
            pyfile=str(self.workdir / pipeline.pipeline_file),
            function_name=pipeline.pipeline_function,
            pipeline_parameters=pipeline_params,
            package_path=pipeline_paths.get_local_pipeline_json_spec_path(self.version),
            type_check=True,
            use_experimental=False,
        )

        docker_refs = [
            DockerBuildResult(
                name=model.name,
                tags=image.repo_tags if image and image.repo_tags else [tag],
                build_type=model.build_type,
            )
            for model, image, tag in image_tags
        ]

        deployment_manifest = PipelineDeployment(
            pipeline_name=pipeline.name,
            pipeline_bucket=pipeline.bucket,
            pipeline_version=self.version,
            json_spec_path=pipeline_paths.get_local_pipeline_json_spec_path(self.version),
            parameter_values=pipeline_params,
            enable_caching=True,
            labels=pipeline.labels,
            project=pipeline.project_id,
            location=pipeline.region,
            service_account=pipeline.service_account,
            pipeline_root=pipeline_env_params.get("pipeline_root"),
            schedule=pipeline.schedule,
            docker_refs=docker_refs,
            compile_env_params=pipeline_env_params,
            network=network
        )
        manifest_path = pipeline_paths.get_local_wanna_manifest_path(self.version)
        PipelineService.write_manifest(deployment_manifest, manifest_path)

        return Path(manifest_path).resolve()

    @staticmethod
    def write_manifest(manifest: PipelineDeployment, path: str) -> None:
        with open(path, "w") as f:
            f.write(manifest.json())

    @staticmethod
    def read_manifest(path: str) -> PipelineDeployment:
        with open(path, "r") as f:
            return PipelineDeployment.parse_obj(json.loads(f.read()))

    def _delete_one_instance(self, instance: PipelineModel) -> None:
        pass

    def _create_one_instance(self, instance: PipelineModel, **kwargs) -> None:
        pass

    def _instance_exists(self, instance: PipelineModel) -> bool:
        pass
