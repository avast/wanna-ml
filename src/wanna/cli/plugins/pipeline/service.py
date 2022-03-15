import atexit
import json
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import typer
import yaml
from caseconverter import snakecase, kebabcase
from google.cloud import aiplatform
from google.cloud.aiplatform import pipeline_jobs
from google.cloud.aiplatform.compat.types import (
    pipeline_state_v1 as gca_pipeline_state_v1,
)
from kfp.v2.compiler.main import compile_pyfile
from python_on_whales import Image

from wanna.cli.docker.service import DockerService
from wanna.cli.models.docker import BaseDockerImageModel, ImageBuildType
from wanna.cli.models.pipeline import PipelineModel
from wanna.cli.models.wanna_config import WannaConfigModel
from wanna.cli.plugins.base.service import BaseService
from wanna.cli.utils.spinners import Spinner
from wanna.cli.utils.time import get_timestamp


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
        self.docker_service = DockerService(
            image_models=(config.docker.images if config.docker else [])
        )
        self.pipeline_store: Dict[str, dict] = {}
        self.workdir = workdir
        self.pipelines_dir = self.workdir / "build" / "pipelines"
        os.makedirs(self.pipelines_dir, exist_ok=True)

    def compile(self, instance_name: str) -> List[Tuple[PipelineModel, Path]]:
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

    def _export_pipeline_params(self, pipeline_instance: PipelineModel):

        # Get pipeline computed values
        pipeline = self.pipeline_store.get(pipeline_instance.name, None)

        # Prepare env params to be exported
        pipeline_env_params = {
            "project_id": pipeline_instance.project_id,
            "pipeline_name": pipeline_instance.name,
            "bucket": pipeline_instance.bucket,
            "region": pipeline_instance.region,
            "pipeline_job_id": f"pipeline-{pipeline_instance.name}-{get_timestamp()}",
            "pipeline_root": f"{pipeline_instance.bucket}/pipeline-root/{kebabcase(pipeline_instance.name).lower()}",
            "pipeline_labels": json.dumps(pipeline_instance.labels)
        }

        # Export Pipeline wanna ENV params to be available during compilation
        pipeline_name_prefix = snakecase(f'{pipeline_instance.name}').upper()
        for key, value in pipeline_env_params.items():
            env_name = snakecase(f"{pipeline_name_prefix}_{key.upper()}").upper()
            os.environ[env_name] = value

        if pipeline:
            image_tags = pipeline.get("image_tags", [])
            for (docker_image_model, _, tag) in image_tags:
                env_name = snakecase(f"{docker_image_model.name}_DOCKER_URI").lower()
                os.environ[env_name] = tag

        # Collect pipeline compile params from wanna config
        if pipeline_instance.pipeline_params and isinstance(pipeline_instance.pipeline_params, Path):
            pipeline_params_path = (self.workdir / pipeline_instance.pipeline_params).resolve()
            pipeline_compile_params = PipelineService._read_pipeline_params(pipeline_params_path)
        elif pipeline_instance.pipeline_params and isinstance(pipeline_instance.pipeline_params, dict):
            pipeline_compile_params = pipeline_instance.pipeline_params
        else:
            pipeline_compile_params = {}

        return pipeline_env_params, pipeline_compile_params

    def _compile_one_instance(self, pipeline_instance: PipelineModel) -> Tuple[PipelineModel, Path, Dict[str, any], Dict[str, str]]:

        image_tags = None
        if pipeline_instance.docker_image_ref:
            image_tags = [self._build_docker_image(docker_image_ref, self.registry, self.version) for docker_image_ref in
                          pipeline_instance.docker_image_ref]

        with Spinner(text=f"Compiling pipeline {pipeline_instance.name}"):
            # Prep build dir
            self.pipeline_dir = self.pipelines_dir / pipeline_instance.name
            os.makedirs(self.pipeline_dir, exist_ok=True)
            pipeline_json_spec_path = (self.pipeline_dir / "pipeline_spec.json").resolve()

            # Collect kubeflow pipeline params for compilation
            pipeline_env_params, pipeline_params = self._export_pipeline_params(pipeline_instance)

            # Compile kubeflow V2 Pipeline
            compile_pyfile(
                pyfile=pipeline_instance.pipeline_file,
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
                "pipeline_env_params": pipeline_env_params
            }

            self.pipeline_store.update({f"{pipeline_instance.name}": compiled_pipeline_meta})

            return pipeline_instance, pipeline_json_spec_path, pipeline_params, pipeline_env_params

    def run(self, instance_name: str, params: Optional[Path] = None, sync: bool = True, service_account: Optional[str] = None, network: Optional[str] = None):

        for pipeline_instance, pipeline_json_spec_path, pipeline_params, pipeline_env_params in self.compile(instance_name):

            with Spinner(text=f"Running pipeline {pipeline_instance.name}"):
                aiplatform.init(project=pipeline_instance.project_id, location=pipeline_instance.region)

                # define pipeline parameters
                pipeline_job_id = pipeline_env_params.get("pipeline_job_id")
                pipeline_root = pipeline_env_params.get("pipeline_root")
                override_params = PipelineService._read_pipeline_params(params) if params else {}

                # Apply override with cli provided params file
                pipeline_params = {**pipeline_params, **override_params}

                # define pipeline job
                pipeline_job = pipeline_jobs.PipelineJob(
                    display_name=pipeline_instance.name,
                    job_id=pipeline_job_id,
                    template_path=str(pipeline_json_spec_path),
                    pipeline_root=pipeline_root,
                    parameter_values=pipeline_params,
                    enable_caching=True,
                    labels=pipeline_instance.labels,
                )

                service_account = service_account or pipeline_instance.service_account

                # TODO: Get Network full name by name - projects/12345/global/networks/myVPC.
                # network = network or pipeline_instance.network_id

                # Cancel pipeline if wanna process exits
                @atexit.register
                def stop_pipeline_job():
                    if pipeline_job.state != gca_pipeline_state_v1.PipelineState.PIPELINE_STATE_SUCCEEDED:
                        typer.echo(f"\N{cross mark} detected exit signal, "
                                   f"shutting down running pipeline {pipeline_instance.name} at {pipeline_job._dashboard_uri()}.")
                        pipeline_job.cancel()
                        pipeline_job.wait()

                # submit pipeline job for execution
                pipeline_job.submit(service_account=service_account, network=network)

                if sync:
                    typer.echo(f"\n\tpipeline dashboard at {pipeline_job._dashboard_uri()}.")
                    pipeline_job.wait()
                    df_pipeline = aiplatform.get_pipeline_df(pipeline=pipeline_instance.name.replace("_", "-"))
                    typer.echo(f"{df_pipeline.info()}")


    def _build_docker_image(
            self, docker_image_ref: str, registry: str, version: str
    ) -> (BaseDockerImageModel, Image, str):
        with Spinner(text=f"Building docker image {docker_image_ref}"):

            docker_image_model = self.docker_service.find_image_model_by_name(docker_image_ref)

            if docker_image_model.build_type == ImageBuildType.provided_image:
                tags = [docker_image_model.image_url]
                image = self.docker_service.build_image(image_model=docker_image_model, tags=[])
            else:
                image_name = f"{self.wanna_project.name}/{docker_image_model.name}"
                tags = self.docker_service.construct_image_tag(
                    registry=registry,
                    project=self.config.gcp_settings.project_id,
                    image_name=image_name,
                    versions=[version, "latest"],
                )

                image = self.docker_service.build_image(
                    image_model=docker_image_model, tags=tags
                )

            typer.echo(f"\n\t Built image with tags {tags}")
            return docker_image_model, image, tags[0],

    def _schedule_all_instance(self) -> None:
        pass

    def _compile_all_instances(self) -> None:
        pass

    def _list_running_instances(self, project_id: str, location: str) -> List[str]:
        pass

    def _delete_one_instance(self, instance: PipelineModel) -> None:
        pass

    def _create_one_instance(self, instance: PipelineModel) -> None:
        pass

    def _instance_exists(self, instance: PipelineModel) -> bool:
        pass

    @staticmethod
    def _read_pipeline_params(path: Path) -> Dict[str,any]:
        with open(path, "r") as f:
            return yaml.safe_load(f)