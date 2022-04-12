import json
import os
from pathlib import Path
from typing import List, Union, Dict, Any, Tuple, Optional

from caseconverter import kebabcase
from smart_open import open
import typer
from google.cloud import aiplatform
from google.cloud.aiplatform import (
    CustomContainerTrainingJob,
    CustomJob,
    CustomPythonPackageTrainingJob,
    CustomTrainingJob,
)
from google.cloud.aiplatform.gapic import WorkerPoolSpec
from google.cloud.aiplatform_v1.types import ContainerSpec, DiskSpec, MachineSpec, PythonPackageSpec
from google.cloud.aiplatform_v1.types.pipeline_state import PipelineState

from wanna.cli.docker.service import DockerService
from wanna.cli.models.training_custom_job import CustomJobModel, TrainingCustomJobModel, WorkerPoolModel, JobManifest, \
    CustomJobType, CustomContainerTrainingJobManifest, CustomPythonPackageTrainingJobManifest, CustomJobManifest
from wanna.cli.models.wanna_config import WannaConfigModel
from wanna.cli.plugins.base.service import BaseService
from wanna.cli.plugins.tensorboard.service import TensorboardService
from wanna.cli.utils.spinners import Spinner
from google.protobuf.json_format import MessageToDict


class JobService(BaseService):
    def __init__(self, config: WannaConfigModel, workdir: Path, version: str = "dev"):
        super().__init__(
            instance_type="job",
            instance_model=TrainingCustomJobModel,
        )
        self.instances = config.jobs
        self.wanna_project = config.wanna_project
        self.bucket_name = config.gcp_profile.bucket
        self.config = config
        self.aiplatform = aiplatform
        self.aiplatform.init(
            project=self.config.gcp_profile.project_id,
            location=self.config.gcp_profile.region,
        )
        self.tensorboard_service = TensorboardService(config=config)
        self.docker_service = DockerService(
            docker_model=config.docker,
            gcp_profile=config.gcp_profile,
            version=version,
            work_dir=workdir,
            wanna_project_name=self.wanna_project.name,
        )
        self.work_dir = workdir
        self.build_dir = workdir / "build"
        self.version = version

    def build(self, instance_name: str, **kwargs) -> List[Tuple[Path, JobManifest]]:
        # Validates yaml
        # Compiles containers
        instances = self._filter_instances_by_name(instance_name)

        built_instances = []
        for instance in instances:
            job_manifest = self._create_instance(instance, **kwargs)
            manifest_path = self._export_job_manifest(job_manifest)
            built_instances.append((manifest_path, job_manifest,))

        return built_instances

    def _make_local_manifest_path(self, job_name: str) -> Path:
        return self.build_dir / f"jobs/{job_name}/job-manifest.json"

    def _make_gcs_manifest_path(self, bucket: str, job_name: str) -> str:
        return f"{bucket}/job-root/{kebabcase(job_name).lower()}"

    def _export_job_manifest(self, manifest: JobManifest) -> Path:
        local_manifest_path = self._make_local_manifest_path(manifest.config.name)
        os.makedirs(local_manifest_path.parent, exist_ok=True)

        with open(local_manifest_path, "w") as fout:
            json_dict = {
                "job_type": manifest.job_type.name,
                "config": manifest.config.dict(),
                "image_refs": manifest.image_refs,
                "payload": manifest.payload
            }
            json_dump = json.dumps(json_dict,
                                   allow_nan=False,
                                   default=lambda o: dict((key, value) for key, value in o.__dict__.items() if value),)
            fout.write(json_dump)

        return local_manifest_path

    @staticmethod
    def read_manifest(manifest_path: Path) -> JobManifest:
        def remove_nulls(d):
            """
            Delete keys with the value ``None`` or `null` in a dictionary, recursively.
            """
            for key, value in list(d.items()):
                if value is None:
                    del d[key]
                elif isinstance(value, dict):
                    remove_nulls(value)
            return d

        with open(manifest_path, "r") as fin:
            json_dict = remove_nulls(json.loads(fin.read()))
            try:
                job_type = CustomJobType[json_dict['job_type']]
                if job_type is CustomJobType.CustomJob:
                    return CustomJobManifest.parse_obj(json_dict)
                elif job_type is CustomJobType.CustomPythonPackageTrainingJob:
                    return CustomPythonPackageTrainingJobManifest.parse_obj(json_dict)
                elif job_type is CustomJobType.CustomContainerTrainingJob:
                    return CustomContainerTrainingJobManifest.parse_obj(json_dict)
                else:
                    raise ValueError("Issue in code, this branch should have not been reached. "
                                     f"job_type {json_dict['job_type']} is unknown")
            except Exception as e:
                typer.echo(f"{e}", err=True)

    def push(self, manifests: List[Tuple[Path, JobManifest]], local: bool = False, **kwargs) -> List[str]:
        # Validates yaml
        # Compiles containers
        # publishes a versioned job-manifest to gcs
        results = []
        for manifest_path, manifest in manifests:
            loaded_manifest = JobService.read_manifest(manifest_path)

            with Spinner(text=f"Pushing job {manifest.config.name}") as s:

                for docker_image_ref in loaded_manifest.image_refs:
                    self.docker_service.push_image_ref(docker_image_ref)

                deployment_bucket = f"{manifest_path.parent}/deployment/release/{self.version}"

                if local:
                    os.makedirs(deployment_bucket, exist_ok=True)
                else:
                    gcs_manifest_path = self._make_gcs_manifest_path(self.config.gcp_settings.bucket, manifest_path.name)
                    deployment_bucket = f"{gcs_manifest_path}/deployment/release/{self.version}"

                manifest_path = str(manifest_path)
                target_manifest = manifest_path.replace(manifest_path, deployment_bucket)

                s.info(f"Uploading wanna job manifest to {target_manifest}")
                with open(target_manifest, "w") as f:
                    f.write(manifest.json())

                results.append(target_manifest)

            return results

    def deploy(self, instance_name: str, **kwargs) -> None:
        # Validates yaml
        # Compiles containers
        # Publishes a versioned job-manifest to gcs
        # Schedules a training job
        pass

    def run(self, jobs: List[str],
            sync: bool = True,
            service_account: Optional[str] = None,
            network: Optional[str] = None,
        ) -> None:

        for manifest_path in jobs:
            manifest = JobService.read_manifest(manifest_path)

            # runs a job from local wanna.yaml
            # runs a job from manifest path
            # Sets Alerts on failed job ???

            if manifest.job_type is CustomJobType.CustomContainerTrainingJobManifest:

                training_job = CustomContainerTrainingJob(*manifest.payload)
            elif manifest.job_type is CustomJobType.CustomPythonPackageTrainingJob:

                training_job = CustomContainerTrainingJob(*manifest.payload)
                with Spinner(text=f"Initiating {manifest.config.name} custom job") as s:
                    s.info(f"Outputs will be saved to {manifest.config.base_output_directory}")
                    training_job.run(
                        machine_type=manifest.config.worker.machine_type,
                        accelerator_type=manifest.config.worker.gpu.accelerator_type,
                        accelerator_count=manifest.config.worker.gpu.count,
                        args=manifest.config.worker.args,
                        base_output_dir=manifest.config.base_output_directory,
                        service_account=manifest.config.service_account,
                        network=manifest.config.network,
                        environment_variables=manifest.config.worker.env,
                        replica_count=manifest.config.worker.replica_count,
                        boot_disk_type=manifest.config.worker.boot_disk_type,
                        boot_disk_size_gb=manifest.config.worker.boot_disk_size_gb,
                        reduction_server_replica_count=manifest.config.reduction_server.replica_count
                        if manifest.config.reduction_server
                        else 0,
                        reduction_server_machine_type=manifest.config.reduction_server.machine_type
                        if manifest.config.reduction_server
                        else None,
                        reduction_server_container_uri=manifest.config.reduction_server.container_uri
                        if manifest.config.reduction_server
                        else None,
                        timeout=manifest.config.timeout_seconds,
                        enable_web_access=manifest.config.enable_web_access,
                        tensorboard=self.tensorboard_service.get_or_create_tensorboard_instance_by_name(
                            manifest.config.tensorboard_ref
                        )
                        if manifest.config.tensorboard_ref
                        else None,
                        sync=True,  # TODO Check
                    )

                training_job.wait_for_resource_creation()
                job_id = training_job.resource_name.split("/")[-1]

                if sync:
                    with Spinner(text=f"Running custom training job {instance.name} in sync mode") as s:
                        s.info(
                            "Job Dashboard in "
                            f"https://console.cloud.google.com/vertex-ai/locations/{instance.region}/training/{job_id}?project={instance.project_id}"  # noqa
                        )
                        training_job.wait()
                else:
                    with Spinner(text=f"Running custom training job {instance.name} in sync mode") as s:
                        s.info(
                            f"Job Dashboard in "
                            f"https://console.cloud.google.com/vertex-ai/locations/{instance.region}/training/{job_id}?project={instance.project_id}"  # noqa
                        )
            else:

                custom_job = CustomJob(*manifest.payload)

                custom_job.run(
                    timeout=manifest.config.timeout_seconds,
                    enable_web_access=manifest.config.enable_web_access,
                    tensorboard=self.tensorboard_service.get_or_create_tensorboard_instance_by_name(
                        manifest.config.tensorboard_ref
                    )
                    if manifest.config.tensorboard_ref
                    else None,
                )

                custom_job.wait_for_resource_creation()
                job_id = custom_job.resource_name.split("/")[-1]

                if sync:
                    with Spinner(text=f"Running custom job {manifest.config.name} in sync mode") as s:
                        s.info(
                            f"Job Dashboard in "
                            f"https://console.cloud.google.com/vertex-ai/locations/{instance.region}/training/{job_id}?project={instance.project_id}"  # noqa
                        )
                        custom_job.wait()
                else:
                    with Spinner(text=f"Running custom job {manifest.config.name} in asyn sync mode") as s:
                        s.info(
                            f"Job Dashboard in "
                            f"https://console.cloud.google.com/vertex-ai/locations/{manifest.config.region}/training/{job_id}?project={manifest.config.project_id}"  # noqa
                        )

    def _create_instance(self, instance: Union[CustomJobModel, TrainingCustomJobModel], **kwargs) -> JobManifest:
        """
        Create one custom job based on TrainingCustomJobModel.
        The function also waits until the job is initiated (no longer pending)

        Args:
            instance: custom job model to create
        """
        if isinstance(instance, TrainingCustomJobModel):
            return self._create_training_job_manifest(instance)
        else:
            image_refs, worker_pool_specs = list(zip(*[self._create_worker_pool_spec(worker) for worker in instance.workers]))
            return CustomJobManifest(
                job_type=CustomJobType.CustomJob,
                config=instance,
                payload={
                    "display_name": instance.name,
                    "worker_pool_specs": [MessageToDict(s) for s in worker_pool_specs],
                    "labels": instance.labels,
                    "staging_bucket": instance.bucket
                },
                image_refs=image_refs
            )



    def _create_training_job_manifest(
        self,
        job_model: TrainingCustomJobModel,
    ) -> Union[CustomPythonPackageTrainingJobManifest, CustomContainerTrainingJobManifest]:
        """"""

        if job_model.worker.python_package:
            image_ref = job_model.worker.python_package.docker_image_ref
            _, _, tag = self.docker_service.get_image(docker_image_ref=job_model.worker.python_package.docker_image_ref)
            result = CustomPythonPackageTrainingJobManifest(
                job_type=CustomJobType.CustomPythonPackageTrainingJob,
                config=job_model,
                payload={
                    "display_name": job_model.name,
                    "python_package_gcs_uri": job_model.worker.python_package.package_gcs_uri,
                    "python_module_name": job_model.worker.python_package.module_name,
                    "container_uri" : tag,
                    "labels": job_model.labels,
                    "staging_bucket": job_model.bucket,
                },
                image_refs=[image_ref]
            )
            return result
        else:
            image_ref = job_model.worker.container.docker_image_ref
            _, _, tag = self.docker_service.get_image(docker_image_ref=job_model.worker.container.docker_image_ref)
            result = CustomContainerTrainingJobManifest(
                job_type=CustomJobType.CustomContainerTrainingJob,
                config=job_model,
                payload={
                    "display_name": job_model.name,
                    "container_uri": tag,
                    "command": job_model.worker.container.command,
                    "labels": job_model.labels,
                    "staging_bucket": job_model.bucket,
                },
                image_refs=[image_ref]
            )
            return result

    def _create_worker_pool_spec(self, worker_pool_model: WorkerPoolModel) -> Tuple[str, WorkerPoolSpec]:
        # TODO: this can be doggy
        image_ref = worker_pool_model.container.docker_image_ref if worker_pool_model.container else worker_pool_model.python_package.docker_image_ref

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
                accelerator_type=worker_pool_model.gpu.accelerator_type if worker_pool_model.gpu else None,
                accelerator_count=worker_pool_model.gpu.count if worker_pool_model.gpu else None,
            ),
            disk_spec=DiskSpec(
                boot_disk_type=worker_pool_model.boot_disk_type, boot_disk_size_gb=worker_pool_model.boot_disk_size_gb
            ),
            replica_count=worker_pool_model.replica_count,
        )

    @staticmethod
    def _create_list_jobs_filter_expr(states: List[PipelineState], job_name: str = None) -> str:
        """
        Creates a filter expression that can be used when listing current jobs on GCP.
        Args:
            states: list of desired states
            job_name: desire job name

        Returns:
            filter expression
        """
        filter_expr = "(" + " OR ".join([f'state="{state.name}"' for state in states]) + ")"
        if job_name:
            filter_expr = filter_expr + f' AND display_name="{job_name}"'
        return filter_expr

    def _list_jobs(self, states: List[PipelineState], job_name: str = None) -> List[CustomTrainingJob]:
        """
        List all custom jobs with given project_id, region with given states.

        Args:
            project_id: gcp project_id
            region: gcp region
            states: list of custom job states, eg [JobState.JOB_STATE_RUNNING, JobState.JOB_STATE_PENDING]
            job_name:

        Returns:
            list of jobs
        """
        filter_expr = self._create_list_jobs_filter_expr(states=states, job_name=job_name)
        jobs = self.aiplatform.CustomTrainingJob.list(filter=filter_expr)
        return jobs  # type: ignore

    def _stop_one_instance(self, instance: TrainingCustomJobModel) -> None:
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
                    with Spinner(text=f"Canceling job {job.display_name}"):
                        job.cancel()
        else:
            typer.echo(f"No running or pending job with name {instance.name}")
