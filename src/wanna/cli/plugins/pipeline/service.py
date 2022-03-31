import atexit
import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from caseconverter import kebabcase, snakecase
from google.cloud import aiplatform
from google.cloud.aiplatform.compat.types import pipeline_state_v1 as gca_pipeline_state_v1
from google.cloud.aiplatform.pipeline_jobs import PipelineJob
from kfp.v2.compiler.main import compile_pyfile
from python_on_whales import Image

from wanna.cli.docker.service import DockerService
from wanna.cli.models.docker import DockerImageModel, ImageBuildType
from wanna.cli.models.pipeline import PipelineMeta, PipelineModel
from wanna.cli.models.wanna_config import WannaConfigModel
from wanna.cli.plugins.base.service import BaseService
from wanna.cli.utils.loaders import load_yaml_path
from wanna.cli.utils.spinners import Spinner
from wanna.cli.utils.time import get_timestamp


def _at_pipeline_exit(pipeline_Name: str, pipeline_job: PipelineJob, sync: bool, spinner: Spinner) -> None:
    @atexit.register
    def stop_pipeline_job():
        if sync and pipeline_job and pipeline_job.state != gca_pipeline_state_v1.PipelineState.PIPELINE_STATE_SUCCEEDED:
            spinner.fail(
                f"detected exit signal, "
                f"shutting down running pipeline {pipeline_Name} "
                f"at {pipeline_job._dashboard_uri()}."
            )
            pipeline_job.cancel()
            pipeline_job.wait()


class PipelineService(BaseService):
    def __init__(self, config: WannaConfigModel, workdir: Path, registry: str = "eu.gcr.io", version: str = "dev"):
        super().__init__(
            instance_type="pipeline",
            instance_model=PipelineModel,
        )
        self.registry = registry
        self.version = version
        self.instances = config.pipelines
        self.wanna_project = config.wanna_project
        self.bucket_name = config.gcp_settings.bucket
        self.config = config
        self.docker_service = DockerService(image_models=(config.docker.images if config.docker else []))
        self.pipeline_store: Dict[str, Dict[str, Any]] = {}
        self.workdir = workdir
        self.pipelines_build_dir = self.workdir / "build" / "pipelines"
        os.makedirs(self.pipelines_build_dir, exist_ok=True)

    def _export_pipeline_params(
        self, pipeline_instance: PipelineModel, images: List[Tuple[DockerImageModel, Optional[Image], str]]
    ):

        # Prepare env params to be exported
        pipeline_env_params = {
            "project_id": pipeline_instance.project_id,
            "pipeline_name": pipeline_instance.name,
            "bucket": pipeline_instance.bucket,
            "region": pipeline_instance.region,
            "pipeline_job_id": f"pipeline-{pipeline_instance.name}-{get_timestamp()}",
            "pipeline_root": f"{pipeline_instance.bucket}/pipeline-root/{kebabcase(pipeline_instance.name).lower()}",
            "pipeline_labels": json.dumps(pipeline_instance.labels),
        }

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

    def _compile_one_instance(self, pipeline_instance: PipelineModel) -> PipelineMeta:

        image_tags = []
        if pipeline_instance.docker_image_ref:
            image_tags = [
                self._build_docker_image(docker_image_ref, self.registry, self.version)
                for docker_image_ref in pipeline_instance.docker_image_ref
            ]

        with Spinner(text=f"Compiling pipeline {pipeline_instance.name}"):
            # Prep build dir
            self.pipeline_dir = self.pipelines_build_dir / pipeline_instance.name
            os.makedirs(self.pipeline_dir, exist_ok=True)
            pipeline_json_spec_path = (self.pipeline_dir / "pipeline_spec.json").resolve()

            # Collect kubeflow pipeline params for compilation
            pipeline_env_params, pipeline_params = self._export_pipeline_params(pipeline_instance, image_tags)

            # Compile kubeflow V2 Pipeline
            compile_pyfile(
                pyfile=str(self.workdir / pipeline_instance.pipeline_file),
                function_name=pipeline_instance.pipeline_function,
                pipeline_parameters=pipeline_params,
                package_path=str(pipeline_json_spec_path),
                type_check=True,
                use_experimental=False,
            )

            # Update pipeline store with computed metadata
            compiled_pipeline_meta = {
                "pipeline_json_spec_path": pipeline_json_spec_path,
                "pipeline_instance": pipeline_instance,
                "image_tags": image_tags,
                "pipeline_parameters": pipeline_params,
                "pipeline_env_params": pipeline_env_params,
            }

            self.pipeline_store.update({f"{pipeline_instance.name}": compiled_pipeline_meta})

            return PipelineMeta(
                json_spec_path=pipeline_json_spec_path,
                config=pipeline_instance,
                images=image_tags,
                parameter_values=pipeline_params,
                compile_env_params=pipeline_env_params,
            )

    def compile(self, instance_name: str) -> List[PipelineMeta]:
        """
        Create an instance with name "name" based on wanna-ml config.
        Args:
            instance_name: The name of the only instance from wanna-ml config that should be created.
                  Set to "all" to create everything from wanna-ml yaml configuration.
        """
        instances = self._filter_instances_by_name(instance_name)

        compiled = []
        for instance in instances:
            compiled.append(self._compile_one_instance(instance))

        return compiled

    def run(
        self,
        pipelines: List[PipelineMeta],
        extra_params_path: Optional[Path] = None,
        sync: bool = True,
        service_account: Optional[str] = None,
        network: Optional[str] = None,
        exit_callback: Callable[[str, PipelineJob, bool, Spinner], None] = _at_pipeline_exit,
    ) -> None:

        for pipeline_meta in pipelines:

            if sync:
                mode = "sync mode"
            else:
                mode = "fire-forget mode"

            with Spinner(text=f"Running pipeline {pipeline_meta.config.name} in {mode}") as s:

                # Publish Containers
                for (model, image, _) in pipeline_meta.images:
                    if model.build_type != ImageBuildType.provided_image:
                        self.docker_service.push_image(image, quiet=True)

                # fetch compiled params
                pipeline_job_id = pipeline_meta.compile_env_params.get("pipeline_job_id")
                pipeline_root = pipeline_meta.compile_env_params.get("pipeline_root")

                # Apply override with cli provided params file
                override_params = load_yaml_path(extra_params_path, self.workdir) if extra_params_path else {}
                pipeline_params = {**pipeline_meta.parameter_values, **override_params}

                service_account = service_account or pipeline_meta.config.service_account

                # TODO: Get Network full name by name - projects/12345/global/networks/myVPC.

                # Define Vertex AI Pipeline job
                pipeline_job = PipelineJob(
                    display_name=pipeline_meta.config.name,
                    job_id=pipeline_job_id,
                    template_path=str(pipeline_meta.json_spec_path),
                    pipeline_root=pipeline_root,
                    parameter_values=pipeline_params,
                    enable_caching=True,
                    labels=pipeline_meta.config.labels,
                    project=pipeline_meta.config.project_id,
                    location=pipeline_meta.config.region,
                )

                # Cancel pipeline if wanna process exits
                exit_callback(pipeline_meta.config.name, pipeline_job, sync, s)

                # submit pipeline job for execution
                pipeline_job.submit(service_account=service_account, network=network)

                if sync:
                    s.info(f"\n\tpipeline dashboard at {pipeline_job._dashboard_uri()}.")
                    pipeline_job.wait()
                    df_pipeline = aiplatform.get_pipeline_df(pipeline=pipeline_meta.config.name.replace("_", "-"))
                    s.info(f"{df_pipeline.info()}")

    def _build_docker_image(
        self, docker_image_ref: str, registry: str, version: str
    ) -> Tuple[DockerImageModel, Optional[Image], str]:
        with Spinner(text=f"Building docker image {docker_image_ref}") as s:

            docker_image_model = self.docker_service.find_image_model_by_name(docker_image_ref)

            if docker_image_model.build_type == ImageBuildType.provided_image:
                tags = [docker_image_model.image_url]
                image = self.docker_service.build_image(image_model=docker_image_model, work_dir=self.workdir, tags=[])
            else:
                image_name = f"{self.wanna_project.name}/{docker_image_model.name}"
                tags = self.docker_service.construct_image_tag(
                    registry=registry,
                    project=self.config.gcp_settings.project_id,
                    image_name=image_name,
                    versions=[version, "latest"],
                )
                image = self.docker_service.build_image(
                    image_model=docker_image_model, work_dir=self.workdir, tags=tags
                )

            s.info(f"Built image with tags {tags}")
            return (
                docker_image_model,
                image,
                tags[0],
            )

    def _list_running_instances(self, project_id: str, location: str) -> List[str]:
        pass

    def _delete_one_instance(self, instance: PipelineModel) -> None:
        pass

    def _create_one_instance(self, instance: PipelineModel, **kwargs) -> None:
        pass

    def _instance_exists(self, instance: PipelineModel) -> bool:
        pass
