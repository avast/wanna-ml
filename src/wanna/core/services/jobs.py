import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import typer
from google.cloud import aiplatform
from google.cloud.aiplatform import CustomTrainingJob
from google.cloud.aiplatform.gapic import WorkerPoolSpec
from google.cloud.aiplatform_v1.types import (
    ContainerSpec,
    DiskSpec,
    MachineSpec,
    PythonPackageSpec,
)
from google.cloud.aiplatform_v1.types.pipeline_state import PipelineState
from google.protobuf.json_format import MessageToDict

from wanna.core.deployment.models import (
    ContainerArtifact,
    JobResource,
    PathArtifact,
    PushMode,
    PushResult,
    PushTask,
)
from wanna.core.deployment.vertex_connector import VertexConnector
from wanna.core.loggers.wanna_logger import get_logger
from wanna.core.models.docker import ImageBuildType
from wanna.core.models.training_custom_job import (
    CustomJobModel,
    HyperparameterTuning,
    JobModelTypeAlias,
    TrainingCustomJobModel,
    WorkerPoolModel,
)
from wanna.core.models.wanna_config import WannaConfigModel
from wanna.core.services.base import BaseService, T
from wanna.core.services.docker import DockerService
from wanna.core.services.path_utils import JobPaths
from wanna.core.services.tensorboard import TensorboardService
from wanna.core.utils.json import remove_nones
from wanna.core.utils.loaders import load_yaml_path

logger = get_logger(__name__)


class JobService(BaseService[JobModelTypeAlias]):
    def __init__(
        self,
        config: WannaConfigModel,
        workdir: Path,
        version: str = "dev",
        push_mode: PushMode = PushMode.all,
        connector: VertexConnector[JobResource[JobModelTypeAlias]] = VertexConnector[
            JobResource[JobModelTypeAlias]
        ](),
    ):
        """
        Service to build, push, deploy and run Vertex AI custom jobs
        Args:
            config (WannaConfigModel): Loaded wanna.yaml
            workdir (Path): Where wanna will conduct it's work
            version (str): Which version of the jobs are working with
        """
        super().__init__(
            instance_type="job",
        )

        self.connector = connector
        self.instances = config.jobs
        self.wanna_project = config.wanna_project
        self.bucket_name = config.gcp_profile.bucket
        self.config = config
        self.tensorboard_service = TensorboardService(config=config)
        self.push_mode = push_mode
        self.workdir = workdir
        self.docker_service = DockerService(
            docker_model=config.docker,  # type: ignore
            gcp_profile=config.gcp_profile,
            version=version,
            work_dir=workdir,
            wanna_project_name=self.wanna_project.name,
            quick_mode=self.push_mode.is_quick_mode(),
        )
        self.build_dir = workdir / "build"
        self.version = version

    def build(self, instance_name: str) -> List[Path]:
        """
        Based on wanna config and setup it creates a JobManifest that
        can later be pushed, deployed or run
        Args:
            instance_name: the give job(s) that will be built
                "all" means it will build all jobs

        Returns:
            Job Manifests and associated local paths where those were built
        """
        instances = self._filter_instances_by_name(instance_name)
        return [self._build(instance) for instance in instances]

    def push(self, manifests: List[Path], local: bool = False) -> PushResult:
        return self.connector.push_artifacts(
            self.docker_service.push_image,
            self._prepare_push(manifests, self.version, local),
        )

    def _prepare_push(
        self, manifests: List[Path], version: str, local: bool = False
    ) -> List[PushTask]:
        """
        Completes the build process buy pushing docker images and pushing manifest files to
        GCS for future execution
        Args:
            manifests: Job Manifests and associated local paths where those were built
            local: allows to publish the manifests locally for inspection and tests

        Returns:
            paths to gs:// paths where the manifests were pushed
        """

        push_tasks = []
        for manifest in manifests:
            manifest_path = str(manifest.resolve())
            loaded_manifest = JobService.read_manifest(self.connector, manifest_path)
            job_paths = JobPaths(
                self.workdir,
                f"gs://{self.bucket_name}",
                loaded_manifest.job_config.name,
            )
            manifest_artifacts, container_artifacts = [], []

            logger.user_info(
                f"Packaging {loaded_manifest.job_config.name} job resources"
            )

            if self.push_mode.can_push_containers():
                for docker_image_ref in loaded_manifest.image_refs:
                    model, image, tag = self.docker_service.get_image(docker_image_ref)
                    if model.build_type != ImageBuildType.provided_image:
                        tags = image.repo_tags if image and image.repo_tags else [tag]
                        container_artifacts.append(
                            ContainerArtifact(name=model.name, tags=tags)
                        )

            if self.push_mode.can_push_gcp_resources():
                gcs_manifest_path = job_paths.get_gcs_job_wanna_manifest_path(version)

                if not local:
                    manifest_artifacts.append(
                        PathArtifact(
                            name=f"{loaded_manifest.job_config.name} job manifest",
                            source=manifest_path,
                            destination=gcs_manifest_path,
                        )
                    )

            push_tasks.append(
                PushTask(
                    container_artifacts=container_artifacts,
                    manifest_artifacts=manifest_artifacts,
                    json_artifacts=[],
                )
            )

        return push_tasks

    @staticmethod
    def run(
        manifests: List[str],
        sync: bool = True,
        hp_params: Optional[Path] = None,
        command_override: Optional[List[str]] = None,
        args_override: Optional[List[Union[str, float, int]]] = None,
    ) -> None:
        """
        Run a Vertex AI Custom Job(s) with a given JobManifest
        Args:
            manifests (List[str]): WANNA JobManifests to be executed
            sync (bool): Allows to run the job in async vs sync mode
            hp_params: path with yaml hp_params for the job
            command_override: override default command from wanna.yaml.
                allows for quickly run a job with multiple commands permutations
            args_override:
                allows for quickly run a job with different args

        """

        for manifest_path in manifests:
            connector = VertexConnector[JobResource[JobModelTypeAlias]]()
            manifest = JobService.read_manifest(connector, manifest_path)

            if isinstance(manifest.job_config, TrainingCustomJobModel):
                if args_override:
                    manifest.job_config.worker.args = args_override

                if manifest.job_config.worker.container and command_override:
                    manifest.job_config.worker.container.command = command_override
                    manifest.job_payload["command"] = command_override

                if manifest.job_config.worker.python_package and command_override:
                    manifest.job_config.worker.python_package.module_name = " ".join(
                        command_override
                    )
                    manifest.job_payload["python_module_name"] = " ".join(
                        command_override
                    )

            elif isinstance(manifest.job_config, CustomJobModel):
                logger.user_info(
                    "command and args override is not supported in CustomJobModel jobs with multiple workers"
                )

            aiplatform.init(
                location=manifest.job_config.region,
                project=manifest.job_config.project_id,
            )

            if isinstance(manifest.job_config, CustomJobModel):
                if hp_params:
                    override_hp_params = load_yaml_path(hp_params, Path("."))
                    manifest_hp_params = (
                        manifest.job_config.hp_tuning.dict()
                        if manifest.job_config.hp_tuning
                        else {}
                    )
                    overriden_hp_tuning = HyperparameterTuning.parse_obj(
                        {**manifest_hp_params, **override_hp_params}
                    )
                    manifest.job_config.hp_tuning = overriden_hp_tuning
                connector.run_custom_job(manifest, sync)
            else:
                connector.run_training_job(manifest, sync)

    def _build(self, instance: Union[CustomJobModel, TrainingCustomJobModel]) -> Path:
        """
        Creates a JobManifest that can later be pushed, deployed or run

        Args:
            instance: custom job model to create
        Returns:
            Job Resource for execution
        """
        job_paths = JobPaths(
            self.workdir,
            instance.bucket or f"gs://{self.config.gcp_profile.bucket}",
            instance.name,
        )
        manifest_path = Path(job_paths.get_local_job_wanna_manifest_path(self.version))
        resource: Union[
            JobResource[CustomJobModel], JobResource[TrainingCustomJobModel]
        ] = (
            self._create_training_job_resource(instance)
            if isinstance(instance, TrainingCustomJobModel)
            else self._create_custom_job_resource(instance)
        )

        return self.write_manifest(manifest_path, resource)

    def _create_custom_job_resource(
        self,
        job_model: CustomJobModel,
    ) -> JobResource[CustomJobModel]:
        image_refs, worker_pool_specs = set(
            zip(
                *[self._create_worker_pool_spec(worker) for worker in job_model.workers]
            )
        )
        labels = {
            "wanna_name": job_model.name,
            "wanna_resource": self.instance_type,
        }
        if job_model.labels:
            labels = {**job_model.labels, **labels}

        network = self._get_resource_network(
            project_id=self.config.gcp_profile.project_id,
            push_mode=self.push_mode,
            resource_network=job_model.network,
            fallback_project_network=self.config.gcp_profile.network,
        )

        encryption_spec_key_name = (
            job_model.encryption_spec
            if job_model.encryption_spec
            else self.config.gcp_profile.kms_key
        )
        env_vars = (
            self.config.gcp_profile.env_vars
            if self.config.gcp_profile.env_vars
            else dict()
        )
        if job_model.env_vars:
            env_vars = {**env_vars, **job_model.env_vars}
        return JobResource[CustomJobModel](
            name=job_model.name,
            project=job_model.project_id,
            location=job_model.region,
            job_config=job_model,
            job_payload={
                "display_name": job_model.name,
                "worker_pool_specs": [
                    remove_nones(MessageToDict(s._pb, preserving_proto_field_name=True))
                    for s in list(worker_pool_specs)
                ],
                "labels": labels,
                "staging_bucket": job_model.bucket,
            },
            image_refs=list(image_refs),
            # during `run` calls, this means changing TensorboardService init
            tensorboard=self.tensorboard_service.get_or_create_tensorboard_instance_by_name(
                job_model.tensorboard_ref
            )
            if job_model.tensorboard_ref
            else None,
            network=network,
            encryption_spec=encryption_spec_key_name,
            environment_variables=env_vars,
        )

    def _create_training_job_resource(
        self,
        job_model: TrainingCustomJobModel,
    ) -> JobResource[TrainingCustomJobModel]:
        """
        Creates a Training Job Manifest that can later be pushed, deployed or run

        Args:
            job_model: Parsed TrainingCustomJobModel from wanna.yaml
        Returns:
            Custom Python on Custom Container training job Manifests
        """
        labels = {
            "wanna_name": job_model.name,
            "wanna_resource": self.instance_type,
        }
        if job_model.labels:
            labels = {**job_model.labels, **labels}
        job_payload: Dict[str, Any] = {}
        if job_model.worker.python_package:
            image_ref = job_model.worker.python_package.docker_image_ref
            _, _, tag = self.docker_service.get_image(
                docker_image_ref=job_model.worker.python_package.docker_image_ref
            )
            job_payload = {
                "display_name": job_model.name,
                "python_package_gcs_uri": job_model.worker.python_package.package_gcs_uri,
                "python_module_name": job_model.worker.python_package.module_name,
                "container_uri": tag,
                "labels": labels,
                "staging_bucket": job_model.bucket,
            }
        elif job_model.worker.container:
            image_ref = job_model.worker.container.docker_image_ref
            _, _, tag = self.docker_service.get_image(
                docker_image_ref=job_model.worker.container.docker_image_ref
            )
            job_payload = {
                "display_name": job_model.name,
                "container_uri": tag,
                "command": job_model.worker.container.command,
                "labels": labels,
                "staging_bucket": job_model.bucket,
            }
        else:
            raise ValueError(
                f"Job {job_model.name} worker must have `container` or `python_package` defined"
            )

        network = self._get_resource_network(
            project_id=self.config.gcp_profile.project_id,
            push_mode=self.push_mode,
            resource_network=job_model.network,
            fallback_project_network=self.config.gcp_profile.network,
        )
        encryption_spec_key_name = (
            job_model.encryption_spec
            if job_model.encryption_spec
            else self.config.gcp_profile.kms_key
        )
        env_vars = (
            self.config.gcp_profile.env_vars
            if self.config.gcp_profile.env_vars
            else dict()
        )
        if job_model.env_vars:
            env_vars = {**env_vars, **job_model.env_vars}
        return JobResource[TrainingCustomJobModel](
            name=job_model.name,
            project=job_model.project_id,
            location=job_model.region,
            job_config=job_model,
            job_payload=job_payload,
            image_refs=[image_ref],
            tensorboard=self.tensorboard_service.get_or_create_tensorboard_instance_by_name(
                job_model.tensorboard_ref
            )
            if job_model.tensorboard_ref
            else None,
            network=network,
            encryption_spec=encryption_spec_key_name,
            environment_variables=env_vars,
        )

    def _create_worker_pool_spec(
        self, worker_pool_model: WorkerPoolModel
    ) -> Tuple[str, WorkerPoolSpec]:
        """
        Converts the friendlier WANNA WorkerPoolModel to aiplatform sdk equivalent
        Args:
            worker_pool_model: Wanna user specified pool details

        Returns:
            The wanna container image_ref to be pushed
            and the aiplatform sdk worker pool spec
        """

        if worker_pool_model.container:
            image_ref = worker_pool_model.container.docker_image_ref
        elif worker_pool_model.python_package:
            image_ref = worker_pool_model.python_package.docker_image_ref
        else:
            raise ValueError(
                "Worker pool does not have container nor python_package. "
                "This means validation has a bug."
            )

        return image_ref, WorkerPoolSpec(
            container_spec=ContainerSpec(
                image_uri=self.docker_service.get_image(image_ref)[2],
                command=worker_pool_model.container.command,
                args=worker_pool_model.args,
                env=worker_pool_model.args,
            )
            if worker_pool_model.container
            else None,
            python_package_spec=PythonPackageSpec(
                executor_image_uri=self.docker_service.get_image(image_ref)[2],
                package_uris=[worker_pool_model.python_package.package_gcs_uri],
                python_module=worker_pool_model.python_package.module_name,
            )
            if worker_pool_model.python_package
            else None,
            machine_spec=MachineSpec(
                machine_type=worker_pool_model.machine_type,
                accelerator_type=worker_pool_model.gpu.accelerator_type
                if worker_pool_model.gpu
                else None,
                accelerator_count=worker_pool_model.gpu.count
                if worker_pool_model.gpu
                else None,
            ),
            disk_spec=DiskSpec(
                boot_disk_type=worker_pool_model.boot_disk.disk_type,
                boot_disk_size_gb=worker_pool_model.boot_disk.size_gb,
            )
            if worker_pool_model.boot_disk
            else None,
            replica_count=worker_pool_model.replica_count,
        )

    @staticmethod
    def _create_list_jobs_filter_expr(
        states: List[PipelineState], job_name: Optional[str] = None
    ) -> str:
        """
        Creates a filter expression that can be used when listing current jobs on GCP.
        Args:
            states: list of desired states
            job_name: desire job name

        Returns:
            filter expression
        """
        filter_expr = (
            "(" + " OR ".join([f'state="{state.name}"' for state in states]) + ")"
        )
        if job_name:
            filter_expr = filter_expr + f' AND display_name="{job_name}"'
        return filter_expr

    def _list_jobs(
        self, states: List[PipelineState], job_name: Optional[str] = None
    ) -> List[CustomTrainingJob]:
        """
        List all custom jobs with given project_id, region with given states.

        Args:
            states: list of custom job states, eg [JobState.JOB_STATE_RUNNING, JobState.JOB_STATE_PENDING]
            job_name:

        Returns:
            list of jobs
        """
        filter_expr = self._create_list_jobs_filter_expr(
            states=states, job_name=job_name
        )
        jobs = aiplatform.CustomTrainingJob.list(filter=filter_expr)
        return jobs  # type: ignore

    def _stop_one_instance(
        self, instance: Union[CustomJobModel, TrainingCustomJobModel]
    ) -> None:
        """
        Pause one all jobs that have the same region and name as "instance".
        First we list all jobs with state running and pending and then
        user is prompted to choose which to kill.

        Args:
            instance: custom job model
        """
        active_jobs = self._list_jobs(
            states=[PipelineState.PIPELINE_STATE_RUNNING, PipelineState.PIPELINE_STATE_PENDING],  # type: ignore
            job_name=instance.name,
        )
        if active_jobs:
            for job in active_jobs:
                should_cancel = typer.prompt(
                    f"Do you want to cancel job {job.display_name} (started at {job.create_time})?"
                )
                if should_cancel:
                    with logger.user_spinner(f"Canceling job {job.display_name}"):
                        job.cancel()
        else:
            logger.user_info(f"No running or pending job with name {instance.name}")

    @staticmethod
    def read_manifest(
        connector: VertexConnector[JobResource[JobModelTypeAlias]],
        manifest_path: str,
    ) -> Union[JobResource[CustomJobModel], JobResource[TrainingCustomJobModel]]:
        """
        Reads a job manifest file

        Args:
            manifest_path (Path): Manifest path to be loaded
            connector VertexConnector[JobResource[JOB]]: connector to read manifest

        Returns:
            JobManifest: Parsed and loaded JobManifest

        """

        json_dict = connector.read(manifest_path)
        try:
            return JobResource[CustomJobModel].parse_obj(json_dict)
        except:
            return JobResource[TrainingCustomJobModel].parse_obj(json_dict)

    def write_manifest(
        self,
        local_manifest_path: Path,
        resource: Union[
            JobResource[TrainingCustomJobModel], JobResource[CustomJobModel]
        ],
    ) -> Path:
        """
        Writes a JobManifest to a local path

        Args:
            local_manifest_path (Path): wanna local path save manifest
            resource (JobResource): the job resource manifest that should be saved locally

        Returns:
            Path: Path where resource manifest was saved to
        """
        encryption_spec_key_name = (
            resource.encryption_spec
            if resource.encryption_spec
            else self.config.gcp_profile.kms_key
        )
        env_vars = (
            self.config.gcp_profile.env_vars
            if self.config.gcp_profile.env_vars
            else dict()
        )
        if resource.environment_variables:
            env_vars = {**env_vars, **resource.environment_variables}
        json_dict = {
            "name": resource.name,
            "project": resource.project,
            "location": resource.location,
            "job_config": resource.job_config.dict(),
            "image_refs": resource.image_refs,
            "job_payload": resource.job_payload,
            "tensorboard": resource.tensorboard,
            "network": resource.network,
            "encryption_spec": encryption_spec_key_name,
            "environment_variables": env_vars,
        }
        json_dump = json.dumps(
            remove_nones(json_dict),
            allow_nan=False,
            default=lambda o: dict(
                (key, value) for key, value in o.__dict__.items() if value
            ),
        )
        self.connector.write(local_manifest_path, json_dump)

        return local_manifest_path

    def _delete_one_instance(self, instance: T) -> None:
        raise NotImplementedError

    def _create_one_instance(self, instance: T, **kwargs) -> None:
        raise NotImplementedError

    def _return_diff(self) -> Tuple[List[T], List[T]]:
        raise NotImplementedError
