from typing import List, Union

import typer
from google.cloud import aiplatform
from google.cloud.aiplatform import CustomContainerTrainingJob, CustomPythonPackageTrainingJob, CustomTrainingJob
from google.cloud.aiplatform_v1.types.pipeline_state import PipelineState

from wanna.cli.models.training_custom_job import TrainingCustomJobModel
from wanna.cli.models.wanna_config import WannaConfigModel
from wanna.cli.plugins.base.service import BaseService
from wanna.cli.utils.spinners import Spinner


class JobService(BaseService):
    def __init__(self, config: WannaConfigModel):
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

    def _create_one_instance(self, instance: TrainingCustomJobModel, **kwargs):
        """
        Create one custom job based on TrainingCustomJobModel.
        The function also waits until the job is initiated (no longer pending)

        Args:
            instance: custom job model to create
        """
        sync = kwargs.get("sync")
        job = self._create_training_job_spec(instance)
        typer.echo(f"Outputs will be saved to {instance.base_output_directory}")
        with Spinner(text="Initiating custom job"):
            job.run(
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
                tensorboard=None,
                sync=False,
            )
        if sync:
            with Spinner(text=f"Running custom job {instance.name}"):
                job.wait()
        else:
            with Spinner(text=f"Creating resources for job {instance.name}"):
                job.wait_for_resource_creation()

    @staticmethod
    def _create_training_job_spec(
        job_model: TrainingCustomJobModel,
    ) -> Union[CustomContainerTrainingJob, CustomPythonPackageTrainingJob]:
        """"""
        if job_model.worker.python_package:
            return CustomPythonPackageTrainingJob(
                display_name=job_model.name,
                python_package_gcs_uri=job_model.worker.python_package.package_gcs_uri,
                python_module_name=job_model.worker.python_package.module_name,
                container_uri=job_model.worker.python_package.executor_image_uri,
                labels=job_model.labels,
                staging_bucket=job_model.bucket,
            )
        else:
            return CustomContainerTrainingJob(
                display_name=job_model.name,
                container_uri=job_model.worker.container.image_uri,
                command=job_model.worker.container.command,
                labels=job_model.labels,
                staging_bucket=job_model.bucket,
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
