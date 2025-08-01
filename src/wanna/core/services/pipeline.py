import importlib
import json
import os
from pathlib import Path
from typing import Any, cast

from caseconverter import snakecase
from google.cloud import aiplatform
from kfp.v2.compiler import Compiler
from python_on_whales import Image

from wanna.core.deployment.artifacts_push import PushResult
from wanna.core.deployment.models import (
    ContainerArtifact,
    JsonArtifact,
    PathArtifact,
    PipelineEnvParams,
    PipelineResource,
    PushMode,
    PushTask,
)
from wanna.core.deployment.vertex_connector import VertexConnector
from wanna.core.loggers.wanna_logger import get_logger
from wanna.core.models.docker import DockerBuildResult, DockerImageModel, ImageBuildType
from wanna.core.models.pipeline import PipelineModel
from wanna.core.models.wanna_config import WannaConfigModel
from wanna.core.services.base import BaseService
from wanna.core.services.docker import DockerService
from wanna.core.services.path_utils import PipelinePaths
from wanna.core.services.tensorboard import TensorboardService
from wanna.core.utils.env import gcp_access_allowed
from wanna.core.utils.loaders import load_yaml_path

logger = get_logger(__name__)


class PipelineService(BaseService[PipelineModel]):
    def __init__(
        self,
        config: WannaConfigModel,
        workdir: Path,
        version: str = "dev",
        push_mode: PushMode = PushMode.all,
        connector: VertexConnector[PipelineResource] = VertexConnector[PipelineResource](),
        skip_execution_cache: bool = False,
    ):
        super().__init__(
            instance_type="pipeline",
        )
        self.connector = connector
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
        self.skip_execution_cache = skip_execution_cache
        self.notification_channels = {
            channel.name: channel for channel in self.config.notification_channels
        }

    def build(self, instance_name: str, pipeline_params_path: Path | None = None) -> list[Path]:
        """
        Create an instance with name "name" based on wanna-ml config.
        Args:
            instance_name: The name of the only instance from wanna-ml config that should be created.
                  Set to "all" to create everything from wanna-ml yaml configuration.
            pipeline_params_path: Path with Kubeflow pipeline params,
                if present will override one from wanna.yaml
        """
        instances = self._filter_instances_by_name(instance_name)
        return [
            self._compile_one_instance(instance, pipeline_params_path) for instance in instances
        ]

    def push(self, manifests: list[Path], local: bool = False) -> PushResult:
        return self.connector.push_artifacts(
            self.docker_service.push_image,
            self._prepare_push(manifests, self.version, local),
        )

    def _prepare_push(
        self, pipelines: list[Path], version: str, local: bool = False
    ) -> list[PushTask]:
        push_tasks = []
        tags2push = set()  # for deduplicating the pushes
        for local_manifest_path in pipelines:
            manifest = PipelineService.read_manifest(self.connector, str(local_manifest_path))
            pipeline_paths = PipelinePaths(
                self.workdir, manifest.pipeline_bucket, manifest.pipeline_name, local=local
            )
            json_artifacts, manifest_artifacts, container_artifacts = [], [], []

            logger.user_info(text=f"Packaging {manifest.pipeline_name} pipeline resources")

            # Push containers if we are running on Internal Teamcity build agent or on all push-mode
            if self.push_mode.can_push_containers():
                for ref in manifest.docker_refs:
                    if ref.build_type != ImageBuildType.provided_image:
                        if any(tag in tags2push for tag in ref.tags):
                            # Filter out tags that are already in some task
                            new_tags = [tag for tag in ref.tags if tag not in tags2push]
                            if new_tags:  # Only add if there are any new tags
                                container_artifacts.append(
                                    ContainerArtifact(name=ref.name, tags=new_tags)
                                )
                        else:
                            container_artifacts.append(
                                ContainerArtifact(name=ref.name, tags=ref.tags)
                            )
                        # Add all tags to the set to track what's been pushed
                        tags2push.update(ref.tags)

            # Push gcp resources if we are running on GCP build agent
            if self.push_mode.can_push_gcp_resources(gcp_access_allowed):
                local_kubeflow_json_spec_path = pipeline_paths.get_local_pipeline_json_spec_path(
                    version
                )

                for v in [version, "latest"]:
                    wanna_manifest_publish_path, kubeflow_json_spec_publish_path = (
                        pipeline_paths.get_wanna_manifest_path(v),
                        pipeline_paths.get_wanna_pipeline_json_spec_path(v),
                    )

                    manifest.json_spec_path = kubeflow_json_spec_publish_path

                    json_artifacts.append(
                        JsonArtifact(
                            name="WANNA pipeline manifest",
                            json_body=manifest.model_dump(),
                            destination=wanna_manifest_publish_path,
                        )
                    )

                    manifest_artifacts.append(
                        PathArtifact(
                            name=f"Kubeflow V2 pipeline spec",
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

    @staticmethod
    def get_pipeline_bucket(bucket: str | None, fallback_bucket: str) -> str:
        if bucket:
            return bucket if bucket.startswith("gs://") else f"gs://{bucket}"
        else:
            return f"gs://{fallback_bucket}"

    def deploy(self, instance_name: str, env: str) -> None:
        instances = self._filter_instances_by_name(instance_name)
        for pipeline in instances:
            logger.user_info(f"Deploying {pipeline.name} version {self.version} to env {env}")
            pipeline_bucket = PipelineService.get_pipeline_bucket(
                pipeline.bucket, self.config.gcp_profile.bucket
            )
            pipeline_paths = PipelinePaths(
                self.workdir, pipeline_bucket, pipeline_name=pipeline.name
            )
            manifest = PipelineService.read_manifest(
                self.connector, pipeline_paths.get_gcs_wanna_manifest_path(self.version)
            )
            self.connector.deploy_pipeline(manifest, pipeline_paths, self.version, env)

    @staticmethod
    def run(
        pipelines: list[str],
        extra_params: Path | None = None,
        sync: bool = True,
    ) -> None:
        connector = VertexConnector[PipelineResource]()
        for manifest_path in pipelines:
            manifest = PipelineService.read_manifest(connector, str(manifest_path))
            aiplatform.init(location=manifest.location, project=manifest.project)
            connector.run_pipeline(manifest, extra_params, sync)

    def _export_pipeline_params(
        self,
        pipeline_paths: PipelinePaths,
        pipeline_instance: PipelineModel,
        version: str,
        images: list[tuple[DockerImageModel, Image | None, str]],
        tensorboard: str | None,
        network: str | None,
        pipeline_params_path: Path | None = None,
    ) -> tuple[PipelineEnvParams, dict[Any, Any] | dict[str, Any]]:
        # Prepare env params to be exported
        pipeline_env_params = {
            "project_id": pipeline_instance.project_id,
            "pipeline_name": pipeline_instance.name,
            "version": version,
            "bucket": pipeline_instance.bucket,
            "region": pipeline_instance.region,
            "pipeline_root": pipeline_paths.get_gcs_pipeline_root(),
            "pipeline_labels": json.dumps(pipeline_instance.labels),
            "pipeline_service_account": (
                pipeline_instance.service_account
                if pipeline_instance.service_account
                else self.config.gcp_profile.service_account
            ),
            "pipeline_experiment": pipeline_instance.experiment,
        }

        if self.config.gcp_profile.kms_key:
            pipeline_env_params["encryption_spec_key_name"] = self.config.gcp_profile.kms_key

        if tensorboard:
            pipeline_env_params["tensorboard"] = tensorboard

        if network:
            pipeline_env_params["pipeline_network"] = network

        # Export Pipeline wanna ENV params to be available during compilation
        pipeline_name_prefix = snakecase(f"{pipeline_instance.name}").upper()
        for key, value in pipeline_env_params.items():
            env_name = snakecase(f"{pipeline_name_prefix}_{key.upper()}").upper()
            os.environ[env_name] = str(value)

        for docker_image_model, _, tag in images:
            env_name = snakecase(f"{docker_image_model.name}_DOCKER_URI").upper()
            os.environ[env_name] = tag

        # Collect pipeline compile params from wanna config
        if pipeline_params_path:
            pipeline_params_path = (self.workdir / pipeline_params_path).resolve()
            pipeline_compile_params = load_yaml_path(pipeline_params_path, self.workdir)
        else:
            if pipeline_instance.pipeline_params and isinstance(
                pipeline_instance.pipeline_params, Path
            ):
                pipeline_params_path = (self.workdir / pipeline_instance.pipeline_params).resolve()
                pipeline_compile_params = load_yaml_path(pipeline_params_path, self.workdir)
            elif pipeline_instance.pipeline_params and isinstance(
                pipeline_instance.pipeline_params, dict
            ):
                pipeline_compile_params = pipeline_instance.pipeline_params
            else:
                pipeline_compile_params = {}

        return pipeline_env_params, pipeline_compile_params

    def _compile_one_instance(
        self, pipeline: PipelineModel, pipeline_params_path: Path | None = None
    ) -> Path:
        image_tags = [
            self.docker_service.get_image(docker_image_ref=docker_image_ref)
            for docker_image_ref in pipeline.docker_image_ref
        ]

        logger.user_info(text=f"Compiling pipeline {pipeline.name}")

        # Prep build dir
        pipeline_bucket = PipelineService.get_pipeline_bucket(
            pipeline.bucket, self.config.gcp_profile.bucket
        )
        pipeline_paths = PipelinePaths(self.workdir, pipeline_bucket, pipeline.name)

        tensorboard = (
            self.tensorboard_service.get_or_create_tensorboard_instance_by_name(
                pipeline.tensorboard_ref
            )
            if pipeline.tensorboard_ref
            and self.push_mode.can_push_gcp_resources(gcp_access_allowed)
            else None
        )

        network = self._get_resource_network(
            project_id=pipeline.project_id,
            push_mode=self.push_mode,
            resource_network=pipeline.network,
            fallback_project_network=self.config.gcp_profile.network,
        )

        labels = {
            "wanna_resource_name": pipeline.name,
            "wanna_resource": self.instance_type,
        }
        if pipeline.sla_hours:
            labels["wanna_sla_hours"] = str(pipeline.sla_hours).replace(".", "_")
        if pipeline.labels:
            labels = {**pipeline.labels, **labels}
        pipeline.labels = labels
        # Collect kubeflow pipeline params for compilation
        pipeline_env_params, pipeline_params = self._export_pipeline_params(
            pipeline_paths,
            pipeline,
            self.version,
            image_tags,
            tensorboard,
            network,
            pipeline_params_path,
        )

        # The current version implies that the pipeline_function is a python import path. ex: module1.module2.function
        mod_name, func_name = pipeline.pipeline_function.rsplit(".", 1)
        module = importlib.import_module(mod_name)
        logger.user_info(f"Using Compiler.compile with function {pipeline.pipeline_function}")
        func = getattr(module, func_name)
        Compiler().compile(
            pipeline_func=func,
            pipeline_parameters=pipeline_params,
            package_path=pipeline_paths.get_local_pipeline_json_spec_path(self.version),
            type_check=True,
        )

        docker_refs = [
            DockerBuildResult(
                name=model.name,
                tags=image.repo_tags if image and image.repo_tags else [tag],
                build_type=model.build_type,
            )
            for model, image, tag in image_tags
        ]

        channels = []
        for ref in pipeline.notification_channels_ref:
            channel = self.notification_channels.get(ref)
            if channel:
                channels.append(channel)
            else:
                raise ValueError(f"{ref} notification channel not specified")

        deployment_manifest = PipelineResource(
            name=f"pipeline {pipeline.name}",
            project=pipeline.project_id,
            location=pipeline.region if pipeline.region else self.config.gcp_profile.region,
            service_account=pipeline.service_account,
            network=network,
            pipeline_name=pipeline.name,
            pipeline_bucket=pipeline_bucket,
            pipeline_version=self.version,
            json_spec_path=pipeline_paths.get_local_pipeline_json_spec_path(self.version),
            parameter_values=pipeline_params,
            enable_caching=False if self.skip_execution_cache else pipeline.enable_caching,
            labels=pipeline.labels,
            pipeline_root=cast(str, pipeline_env_params["pipeline_root"]),
            schedule=pipeline.schedule,
            docker_refs=docker_refs,
            compile_env_params=pipeline_env_params,
            notification_channels=channels,
            encryption_spec_key_name=self.config.gcp_profile.kms_key,
            experiment=pipeline.experiment,
        )

        manifest_path = pipeline_paths.get_local_wanna_manifest_path(self.version)
        self.connector.write(manifest_path, deployment_manifest.json())
        return Path(manifest_path).resolve()

    @staticmethod
    def read_manifest(connector: VertexConnector[PipelineResource], path: str) -> PipelineResource:
        return PipelineResource.model_validate(connector.read(path))

    def _delete_one_instance(self, instance: PipelineModel) -> None:
        raise NotImplementedError

    def _create_one_instance(self, instance: PipelineModel, **kwargs) -> None:
        raise NotImplementedError

    def _instance_exists(self, instance: PipelineModel) -> bool:
        raise NotImplementedError
