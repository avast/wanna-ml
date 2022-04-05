import atexit
import json
import os
import zipfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd
from caseconverter import kebabcase, snakecase
from google.api_core.exceptions import NotFound
from google.cloud import aiplatform, scheduler_v1
from google.cloud.aiplatform.compat.types import pipeline_state_v1 as gca_pipeline_state_v1
from google.cloud.aiplatform.pipeline_jobs import PipelineJob
from google.cloud.functions_v1.services.cloud_functions_service import CloudFunctionsServiceClient
from kfp.v2.compiler.main import compile_pyfile
from python_on_whales import Image
from smart_open import open

from wanna.cli.docker.service import DockerService
from wanna.cli.models.docker import DockerImageModel, ImageBuildType
from wanna.cli.models.pipeline import PipelineDeployment, PipelineMeta, PipelineModel
from wanna.cli.models.wanna_config import WannaConfigModel
from wanna.cli.plugins.base.service import BaseService
from wanna.cli.utils import templates
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
    def __init__(self, config: WannaConfigModel, workdir: Path, version: str = "dev"):
        super().__init__(
            instance_type="pipeline",
            instance_model=PipelineModel,
        )
        self.instances = config.pipelines
        self.wanna_project = config.wanna_project
        self.bucket_name = config.gcp_settings.bucket
        self.config = config
        self.pipeline_store: Dict[str, Dict[str, Any]] = {}
        self.workdir = workdir
        self.pipelines_build_dir = self.workdir / "build" / "pipelines"
        os.makedirs(self.pipelines_build_dir, exist_ok=True)
        self.docker_service = DockerService(
            image_models=(config.docker.images if config.docker else []),
            registry=config.docker.registry or f"{self.config.gcp_settings.region}-docker.pkg.dev",
            repository=config.docker.repository,
            version=version,
            work_dir=workdir,
            wanna_project_name=self.wanna_project.name,
            project_id=self.config.gcp_settings.project_id,
        )

    def build(self, instance_name: str) -> List[Tuple[PipelineMeta, Path]]:
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

    def push(
        self, pipelines: List[Tuple[PipelineMeta, Path]], version: str, local: bool = False
    ) -> List[Tuple[str, str]]:

        results = []
        for (pipeline_meta, manifest_path) in pipelines:
            manifest = PipelineService.read_manifest(str(manifest_path))

            with Spinner(text=f"Pushing pipeline {manifest.pipeline_name}") as s:

                # Push containers
                for (model, image, tags) in pipeline_meta.images:
                    if model.build_type != ImageBuildType.provided_image:
                        s.info(f"Pushing docker tag {tags}")
                        self.docker_service.push_image(image, quiet=True)

                # upload manifests
                pipeline_dir_path = self.pipelines_build_dir / f"{manifest.pipeline_name}"
                pipeline_dir = str(pipeline_dir_path)
                pipeline_json_spec_path = str(pipeline_dir_path / "pipeline_spec.json")

                deployment_bucket = f"{manifest.pipeline_root}/deployment/release/{version}"

                if local:
                    os.makedirs(deployment_bucket, exist_ok=True)

                target_manifest = str(manifest_path).replace(pipeline_dir, deployment_bucket)
                target_json_spec_path = pipeline_json_spec_path.replace(pipeline_dir, deployment_bucket)
                manifest.json_spec_path = target_json_spec_path

                s.info(f"Uploading wanna running manifest to {target_manifest}")
                with open(target_manifest, "w") as f:
                    f.write(manifest.json())

                s.info(f"Uploading vertex ai pipeline spec to {target_json_spec_path}")
                with open(pipeline_json_spec_path, "r") as fin:
                    with open(target_json_spec_path, "w") as fout:
                        fout.write(fin.read())

                results.append(
                    (
                        target_manifest,
                        target_json_spec_path,
                    )
                )

        return results

    def deploy(self, instance_name: str, version: str, env: str, local: bool = False):

        instances = self._filter_instances_by_name(instance_name)
        for pipeline in instances:
            with Spinner(text=f"Deploying {pipeline.name} version {version} to env {env}") as s:
                pipeline_root = self._make_pipeline_root(pipeline.bucket, pipeline.name)
                deployment_manifest_path = f"{pipeline_root}/deployment/release/{version}/wanna_manifest.json"
                manifest = PipelineService.read_manifest(deployment_manifest_path)
                parent = f"projects/{manifest.project}/locations/{manifest.location}"
                function = self._upsert_cloud_function(
                    parent=parent, manifest=manifest, pipeline_root=pipeline_root, env=env, version=version, spinner=s
                )

                if manifest.schedule:
                    self._upsert_cloud_scheduler(
                        function=function,
                        parent=parent,
                        manifest=manifest,
                        pipeline_root=pipeline_root,
                        env=env,
                        version=version,
                        spinner=s,
                    )
                else:
                    s.warn("Deployment Manifest does not have a schedule set. Skipping Cloud Scheduler sync")

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

            mode = "sync mode" if sync else "fire-forget mode"

            with Spinner(text=f"Running pipeline {manifest.pipeline_name} in {mode}") as s:

                # fetch compiled params
                pipeline_job_id = f"pipeline-{manifest.pipeline_name}-{get_timestamp()}"

                # Apply override with cli provided params file
                override_params = load_yaml_path(extra_params_path, Path(".")) if extra_params_path else {}
                pipeline_params = {**manifest.parameter_values, **override_params}

                service_account = service_account or manifest.service_account

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
        self, pipeline_instance: PipelineModel, images: List[Tuple[DockerImageModel, Optional[Image], str]]
    ):

        # Prepare env params to be exported
        pipeline_env_params = {
            "project_id": pipeline_instance.project_id,
            "pipeline_name": pipeline_instance.name,
            "bucket": pipeline_instance.bucket,
            "region": pipeline_instance.region,
            "pipeline_job_id": f"pipeline-{pipeline_instance.name}-{get_timestamp()}",
            "pipeline_root": self._make_pipeline_root(pipeline_instance.bucket, pipeline_instance.name),
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

    def _compile_one_instance(self, pipeline_instance: PipelineModel) -> Tuple[PipelineMeta, Path]:

        image_tags = []
        if pipeline_instance.docker_image_ref:
            with Spinner(text="Building docker images"):
                print(pipeline_instance.docker_image_ref)
                image_tags = [
                    self.docker_service.build_image(
                        docker_image_ref=docker_image_ref,
                    )
                    for docker_image_ref in pipeline_instance.docker_image_ref
                ]

        with Spinner(text=f"Compiling pipeline {pipeline_instance.name}"):
            # Prep build dir
            pipeline_dir = self.pipelines_build_dir / pipeline_instance.name
            os.makedirs(pipeline_dir, exist_ok=True)
            pipeline_json_spec_path = (pipeline_dir / "pipeline_spec.json").resolve()

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

            pipeline_meta = PipelineMeta(
                json_spec_path=pipeline_json_spec_path,
                config=pipeline_instance,
                images=image_tags,
                parameter_values=pipeline_params,
                compile_env_params=pipeline_env_params,
            )

            deployment_manifest = PipelineDeployment(
                pipeline_name=pipeline_meta.config.name,
                json_spec_path=str(pipeline_meta.json_spec_path),
                parameter_values=pipeline_meta.parameter_values,
                enable_caching=True,
                labels=pipeline_meta.config.labels,
                project=pipeline_meta.config.project_id,
                location=pipeline_meta.config.region,
                service_account=pipeline_meta.config.service_account,
                pipeline_root=pipeline_env_params.get("pipeline_root"),
                schedule=pipeline_meta.config.schedule,
            )

            manifest_path = pipeline_dir / "wanna_manifest.json"
            PipelineService.write_manifest(deployment_manifest, manifest_path)

            return (
                pipeline_meta,
                manifest_path,
            )

    def _is_gcs_path(self, path: str):
        return path.startswith("gs://")

    def _upsert_cloud_function(
        self, parent: str, manifest: PipelineDeployment, pipeline_root: str, version: str, env: str, spinner: Spinner
    ) -> Tuple[str, str]:

        spinner.info(f"Deploying {manifest.pipeline_name} cloud function with version {version} to env {env}")
        pipeline_functions_dir = self.pipelines_build_dir / manifest.pipeline_name / "functions"
        os.makedirs(pipeline_functions_dir, exist_ok=True)
        local_functions_package = pipeline_functions_dir / "package.zip"
        functions_gcs_path_dir = f"{pipeline_root}/deployment/release/{version}/functions"
        functions_gcs_path = f"{functions_gcs_path_dir}/package.zip"
        function_name = f"{parent}/functions/{manifest.pipeline_name}-{env}"

        cloud_function = templates.render_template(
            Path("scheduler_cloud_function.py"),
            manifest=dict(manifest),
            labels=json.dumps(manifest.labels, separators=(",", ":")),
        )

        requirements = templates.render_template(
            Path("scheduler_cloud_function_requirements.txt"), manifest=dict(manifest)
        )

        with zipfile.ZipFile(local_functions_package, "w") as z:
            z.writestr("main.py", cloud_function)
            z.writestr("requirements.txt", requirements)

        if not self._is_gcs_path(functions_gcs_path_dir):
            os.makedirs(functions_gcs_path_dir, exist_ok=True)

        self._sync_cloud_function_package(str(local_functions_package), functions_gcs_path)

        cf = CloudFunctionsServiceClient()
        function_url = f"https://{manifest.project}-{manifest.location}.cloudfunctions.net/{function_name}-v1"
        function = {
            "name": function_name,
            "description": f"wanna {manifest.pipeline_name} function for {env} pipeline",
            "source_archive_url": functions_gcs_path,
            "entry_point": "process_request",
            "runtime": "python39",
            "https_trigger": {
                "url": f"https://{manifest.project}-{manifest.location}.cloudfunctions.net/{function_name}-v1",
            },
            # TODO: timeout
            # TODO: service_account_email
            "labels": manifest.labels,
            # TODO: environment_variables
        }

        try:
            cf.get_function({"name": function_name})
            cf.update_function({"function": function}).result()
            return (
                function_name,
                function_url,
            )
        except NotFound:
            cf.create_function({"location": manifest.location, "function": function}).result()
            return (
                function_name,
                function_url,
            )

    def _sync_cloud_function_package(self, local_functions_package: str, functions_gcs_path: str):
        with open(local_functions_package, "rb") as f:
            with open(functions_gcs_path, "wb") as fout:
                fout.write(f.read())

    def _upsert_cloud_scheduler(
        self,
        function: Tuple[str, str],
        parent: str,
        manifest: PipelineDeployment,
        pipeline_root: str,
        version: str,
        env: str,
        spinner: Spinner,
    ) -> None:
        client = scheduler_v1.CloudSchedulerClient()
        pipeline_spec_path = f"{pipeline_root}/deployment/release/{version}/pipeline_spec.json"
        job_name = f"{parent}/jobs/{manifest.pipeline_name}-{env}"
        function_name, function_url = function

        spinner.info(f"Deploying {manifest.pipeline_name} cloud scheduler with version {version} to env {env}")
        body = {"pipeline_spec_uri": pipeline_spec_path, "parameter_values": manifest.parameter_values}  # TODO extend

        http_target = {
            "uri": function_url,
            "body": json.dumps(body, separators=(",", ":")).encode(),
            "headers": {
                "Content-Type": "application/octet-stream",
                "User-Agent": "Google-Cloud-Scheduler",
                "Wanna-Pipeline-Version": version,
            },
        }

        job = {
            "name": job_name,
            "description": f"wanna {manifest.pipeline_name} scheduler for  {env} pipeline",
            "http_target": http_target,
            "schedule": manifest.schedule.cron,
            "time_zone": manifest.schedule.timezone,
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

    def _make_pipeline_root(self, bucket: str, pipeline_name: str):
        return f"{bucket}/pipeline-root/{kebabcase(pipeline_name).lower()}"

    @staticmethod
    def write_manifest(manifest: PipelineDeployment, path: Path) -> None:
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
