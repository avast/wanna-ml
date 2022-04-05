from pathlib import Path
from typing import List, Union

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
from wanna.cli.models.training_custom_job import CustomJobModel, TrainingCustomJobModel, WorkerPoolModel
from wanna.cli.models.wanna_config import WannaConfigModel
from wanna.cli.plugins.base.service import BaseService
from wanna.cli.plugins.tensorboard.service import TensorboardService
from wanna.cli.utils.spinners import Spinner


class JobService(BaseService):
    def __init__(self, config: WannaConfigModel, workdir: Path, version: str = "dev"):
        super().__init__(
            instance_type="job",
            instance_model=TrainingCustomJobModel,
        )
        self.instances = config.jobs
        self.wanna_project = config.wanna_project
        self.bucket_name = config.gcp_settings.bucket
        self.config = config
        self.aiplatform = aiplatform
        self.aiplatform.init(
            project=self.config.gcp_settings.project_id,
            location=self.config.gcp_settings.region,
        )
        self.tensorboard_service = TensorboardService(config=config)
        self.docker_service = DockerService(
            image_models=(config.docker.images if config.docker else []),
            registry=config.docker.registry or f"{self.config.gcp_settings.region}-docker.pkg.dev",
            repository=config.docker.repository,
            version=version,
            work_dir=workdir,
            wanna_project_name=self.wanna_project.name,
            project_id=self.config.gcp_settings.project_id,
        )

    def _create_one_instance(self, instance: Union[CustomJobModel, TrainingCustomJobModel], **kwargs):
        """
        Create one custom job based on TrainingCustomJobModel.
        The function also waits until the job is initiated (no longer pending)

        Args:
            instance: custom job model to create
        """
        sync = kwargs.get("sync")

        if isinstance(instance, TrainingCustomJobModel):
            with Spinner(text=f"Initiating {instance.name} custom job") as s:
                training_job = self._create_training_job_spec(instance)
                s.info(f"Outputs will be saved to {instance.base_output_directory}")
                training_job.run(
                    machine_type=instance.worker.machine_type,
                    accelerator_type=instance.worker.gpu.accelerator_type,
                    accelerator_count=instance.worker.gpu.count,
                    args=instance.worker.args,
                    base_output_dir=instance.base_output_directory,
                    service_account=instance.service_account,
                    network=instance.network,
                    environment_variables=instance.worker.env,
                    replica_count=instance.worker.replica_count,
                    boot_disk_type=instance.worker.boot_disk_type,
                    boot_disk_size_gb=instance.worker.boot_disk_size_gb,
                    reduction_server_replica_count=instance.reduction_server.replica_count
                    if instance.reduction_server
                    else 0,
                    reduction_server_machine_type=instance.reduction_server.machine_type
                    if instance.reduction_server
                    else None,
                    reduction_server_container_uri=instance.reduction_server.container_uri
                    if instance.reduction_server
                    else None,
                    timeout=instance.timeout_seconds,
                    enable_web_access=instance.enable_web_access,
                    tensorboard=self.tensorboard_service.get_or_create_tensorboard_instance_by_name(
                        instance.tensorboard_ref
                    )
                    if instance.tensorboard_ref
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

            custom_job = CustomJob(
                display_name=instance.name,
                worker_pool_specs=[self._create_worker_pool_spec(worker) for worker in instance.workers],
                labels=instance.labels,
                staging_bucket=instance.bucket,
            )

            custom_job.run(
                timeout=instance.timeout_seconds,
                enable_web_access=instance.enable_web_access,
                tensorboard=self.tensorboard_service.get_or_create_tensorboard_instance_by_name(
                    instance.tensorboard_ref
                )
                if instance.tensorboard_ref
                else None,
            )

            custom_job.wait_for_resource_creation()
            job_id = custom_job.resource_name.split("/")[-1]

            if sync:
                with Spinner(text=f"Running custom job {instance.name} in sync mode") as s:
                    s.info(
                        f"Job Dashboard in "
                        f"https://console.cloud.google.com/vertex-ai/locations/{instance.region}/training/{job_id}?project={instance.project_id}"  # noqa
                    )
                    custom_job.wait()
            else:
                with Spinner(text=f"Running custom job {instance.name} in asyn sync mode") as s:
                    s.info(
                        f"Job Dashboard in "
                        f"https://console.cloud.google.com/vertex-ai/locations/{instance.region}/training/{job_id}?project={instance.project_id}"  # noqa
                    )

    def _create_training_job_spec(
        self,
        job_model: TrainingCustomJobModel,
    ) -> Union[CustomContainerTrainingJob, CustomPythonPackageTrainingJob]:
        """"""

        if job_model.worker.python_package:
            container = self.docker_service.build_image(
                docker_image_ref=job_model.worker.python_package.docker_image_ref
            )
            tag = container[2]
            return CustomPythonPackageTrainingJob(
                display_name=job_model.name,
                python_package_gcs_uri=job_model.worker.python_package.package_gcs_uri,
                python_module_name=job_model.worker.python_package.module_name,
                container_uri=tag,
                labels=job_model.labels,
                staging_bucket=job_model.bucket,
            )
        else:
            container = self.docker_service.build_image(docker_image_ref=job_model.worker.container.docker_image_ref)
            tag = container[2]
            return CustomContainerTrainingJob(
                display_name=job_model.name,
                container_uri=tag,
                command=job_model.worker.container.command,
                labels=job_model.labels,
                staging_bucket=job_model.bucket,
            )

    def _create_worker_pool_spec(self, worker_pool_model: WorkerPoolModel) -> WorkerPoolSpec:
        return WorkerPoolSpec(
            container_spec=ContainerSpec(
                image_uri=self.docker_service.build_image(worker_pool_model.container.docker_image_ref)[2],
                command=worker_pool_model.container.command,
                args=worker_pool_model.args,
                env=worker_pool_model.args,
            )
            if worker_pool_model.container
            else None,
            python_package_spec=PythonPackageSpec(
                executor_image_uri=self.docker_service.build_image(worker_pool_model.python_package.docker_image_ref)[
                    2
                ],
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
