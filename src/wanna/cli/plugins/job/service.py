from typing import List

import typer
from google.cloud.aiplatform_v1.services.job_service import JobServiceClient
from google.cloud.aiplatform_v1.types import (
    CustomJob,
    CustomJobSpec,
    WorkerPoolSpec,
    PythonPackageSpec,
    GcsDestination,
    Scheduling,
    MachineSpec,
    ContainerSpec,
)
from google.cloud.aiplatform_v1.types import ListCustomJobsRequest
from google.cloud.aiplatform_v1.types.job_state import JobState
from google.protobuf.duration_pb2 import Duration
from waiting import wait
from wanna.cli.models.training_custom_job import (
    TrainingCustomJobModel,
    WorkerPoolSpecModel,
)
from wanna.cli.models.wanna_config import WannaConfigModel
from wanna.cli.plugins.base.service import BaseService
from wanna.cli.utils.spinners import Spinner


class JobService(BaseService):
    def __init__(self, config: WannaConfigModel):
        super().__init__(
            instance_type="job",
            instance_model=TrainingCustomJobModel,
        )
        self.instances = config.training_custom_jobs
        self.wanna_project = config.wanna_project
        self.bucket_name = config.gcp_settings.bucket
        self.config = config
        self.job_client = JobServiceClient(
            client_options={"api_endpoint": f"{self.config.gcp_settings.region}-aiplatform.googleapis.com"}
        )


    def _create_one_instance(self, instance: TrainingCustomJobModel):
        """
        Create one custom job based on TrainingCustomJobModel.
        The function also waits until the job is initiated (no longer pending)

        Args:
            instance: custom job model to create
        """
        job_spec = self._create_instance_request(instance)
        job = CustomJob(display_name=instance.name, job_spec=job_spec)
        job_request = self.job_client.create_custom_job(
            parent=f"projects/{instance.project_id}/locations/{instance.region}",
            custom_job=job,
        )
        typer.echo(
            f"Outputs will be saved to {job.job_spec.base_output_directory.output_uri_prefix}"
        )
        with Spinner(text="Initiating custom job"):
            wait(
                lambda: self.job_client.get_custom_job(name=job_request.name).state
                in [
                    JobState.JOB_STATE_FAILED,
                    JobState.JOB_STATE_SUCCEEDED,
                    JobState.JOB_STATE_RUNNING,
                ],
                timeout_seconds=600,
                sleep_seconds=10,
                waiting_for="Initiating Custom Training Job",
            )
        job_state = self.job_client.get_custom_job(name=job_request.name).state
        if job_state == JobState.JOB_STATE_RUNNING:
            typer.echo(f"Job {instance.name} is running.")
        elif job_state == JobState.JOB_STATE_SUCCEEDED:
            typer.echo(f"Job {instance.name} succeeded.")
        else:
            typer.echo(
                f"Job {instance.name} initiating failed or took longer than usual, check logs {job_state.name}."
            )

    @staticmethod
    def _create_worker_pool_spec(
            worker_pool: WorkerPoolSpecModel
    ) -> WorkerPoolSpec:
        """
        Create GCP API friendly WorkerPoolSpec from WorkerPoolSpecModel.
        This creates one worker_pool (eg. master or reduction server etc.)
        and should be called for each role/task.

        Args:
            worker_pool: worker pool spec model

        Returns:
            GCP API friendly worker pool spec
        """
        if worker_pool.python_package_spec:
            python_package_spec = PythonPackageSpec(
                executor_image_uri=worker_pool.python_package_spec.executor_image_uri,
                package_uris=worker_pool.python_package_spec.package_uris,
                python_module=worker_pool.python_package_spec.python_module,
                args=worker_pool.python_package_spec.args,
                env=worker_pool.python_package_spec.env,
            )
            container_spec = None
        else:
            python_package_spec = None
            container_spec = ContainerSpec(
                image_uri=worker_pool.container_spec.image_uri,
                command=worker_pool.container_spec.command,
                args=worker_pool.container_spec.args,
                env=worker_pool.container_spec.env,
            )
        machine_spec = MachineSpec(
            machine_type=worker_pool.machine_type,
            accelerator_type=worker_pool.gpu.accelerator_type
            if worker_pool.gpu
            else None,
            accelerator_count=worker_pool.gpu.count if worker_pool.gpu else None,
        )

        worker_pool_spec = WorkerPoolSpec(
            python_package_spec=python_package_spec,
            container_spec=container_spec,
            machine_spec=machine_spec,
            disk_spec={
                "boot_disk_type": worker_pool.boot_disk_type,
                "boot_disk_size_gb": worker_pool.boot_disk_size_gb,
            },
            replica_count=worker_pool.replica_count,
        )
        return worker_pool_spec

    def _create_instance_request(
        self, instance: TrainingCustomJobModel
    ) -> CustomJobSpec:
        """
        Create a custom job that could be later directly sent to GCP API.
        Args:
            instance: custom job model

        Returns:
            GCP API friendly custom job spec
        """
        master = self._create_worker_pool_spec(instance.worker_pool_specs.master)
        worker = (
            self._create_worker_pool_spec(instance.worker_pool_specs.worker)
            if instance.worker_pool_specs.worker
            else WorkerPoolSpec()
        )
        reduction_server = (
            self._create_worker_pool_spec(instance.worker_pool_specs.reduction_server)
            if instance.worker_pool_specs.reduction_server
            else WorkerPoolSpec()
        )
        evaluator = (
            self._create_worker_pool_spec(instance.worker_pool_specs.evaluator)
            if instance.worker_pool_specs.evaluator
            else WorkerPoolSpec()
        )

        base_output_directory = GcsDestination(
            output_uri_prefix=f"gs://{instance.bucket}{instance.base_output_directory}"
        )
        scheduling = Scheduling(timeout=Duration(seconds=instance.timeout_seconds))
        return CustomJobSpec(
            worker_pool_specs=[master, worker, reduction_server, evaluator],
            network=instance.network,
            tensorboard=None,  # TODO: add tensorboard support
            service_account=instance.service_account,
            scheduling=scheduling,
            base_output_directory=base_output_directory,
            enable_web_access=instance.enable_web_access,
        )

    @staticmethod
    def _create_list_jobs_filter_expr(
            states: List[JobState], job_name: str = None
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
        self, project_id: str, region: str, states: List[JobState], job_name: str = None
    ) -> List[CustomJob]:
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
        filter_expr = self._create_list_jobs_filter_expr(
            states=states, job_name=job_name
        )
        resp = self.job_client.list_custom_jobs(
            ListCustomJobsRequest(
                parent=f"projects/{project_id}/locations/{region}",
                filter=filter_expr,
            )
        )
        return [job for job in resp.custom_jobs]

    def _stop_one_instance(self, instance: TrainingCustomJobModel) -> None:
        """
        Pause one all jobs that have the same region and name as "instance".
        First we list all jobs with state running and pending and then
        user is prompted to choose which to kill.

        Args:
            instance: custom job model
        """
        active_jobs = self._list_jobs(
            project_id=instance.project_id,
            region=instance.region,
            states=[JobState.JOB_STATE_RUNNING, JobState.JOB_STATE_PENDING],
            job_name=instance.name,
        )
        if active_jobs:
            for job in active_jobs:
                should_cancel = typer.prompt(
                    f"Do you want to cancel job {job.display_name} (started at {job.create_time})?"
                )
                if should_cancel:
                    with Spinner(text=f"Canceling job {job.display_name}"):
                        self.job_client.cancel_custom_job(name=job.name)
        else:
            typer.echo(f"No running or pending job with name {instance.name}")
