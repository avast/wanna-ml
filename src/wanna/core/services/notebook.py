import itertools
import subprocess
from pathlib import Path
from threading import Thread
from typing import List, Optional, Tuple

import typer
from google.api_core import exceptions
from google.cloud import compute_v1
from google.cloud.notebooks_v1.services.notebook_service import NotebookServiceClient
from google.cloud.notebooks_v1.types import (
    ContainerImage,
    CreateInstanceRequest,
    Instance,
    VmImage,
)
from waiting import wait

from wanna.core.deployment.models import PushMode
from wanna.core.loggers.wanna_logger import get_logger
from wanna.core.models.notebook import NotebookModel
from wanna.core.models.wanna_config import WannaConfigModel
from wanna.core.services.base import BaseService
from wanna.core.services.docker import DockerService
from wanna.core.services.tensorboard import TensorboardService
from wanna.core.utils import templates
from wanna.core.utils.config_enricher import email_fixer
from wanna.core.utils.gcp import (
    construct_vm_image_family_from_vm_image,
    upload_string_to_gcs,
)

logger = get_logger(__name__)


class NotebookService(BaseService[NotebookModel]):
    def __init__(
        self,
        config: WannaConfigModel,
        workdir: Path,
        owner: Optional[str] = None,
        version: str = "dev",
    ):
        super().__init__(
            instance_type="notebook",
        )
        self.version = version
        self.instances = config.notebooks
        self.wanna_project = config.wanna_project
        self.bucket_name = config.gcp_profile.bucket
        self.notebook_client = NotebookServiceClient()
        self.config = config
        self.docker_service = (
            DockerService(
                docker_model=config.docker,
                gcp_profile=config.gcp_profile,
                version=version,
                work_dir=workdir,
                wanna_project_name=self.wanna_project.name,
            )
            if config.docker
            else None
        )

        self.owner = owner
        self.tensorboard_service = TensorboardService(config=config)

    def create(self, instance_name: str, **kwargs) -> None:
        """
        Create an instance with name "name" based on wanna-ml config.

        Args:
            instance_name: The name of the only instance from wanna-ml config that should be created.
                  Set to "all" to create everything from wanna-ml yaml configuration.
        """
        instances = self._filter_instances_by_name(instance_name)

        for instance in instances:
            t = Thread(
                target=self._create_one_instance, args=(instance,), kwargs={**kwargs}
            )
            t.start()

    def delete(self, instance_name: str) -> None:
        """
        Delete an instance with name "name" based on wanna-ml config if exists on GCP.

        Args:
            instance_name: The name of the only instance from wanna-ml config that should be deleted.
                  Set to "all" to create all from configuration.
        """
        instances = self._filter_instances_by_name(instance_name)

        for instance in instances:
            t = Thread(target=self._delete_one_instance, args=(instance,))
            t.start()

    def _delete_one_instance(self, notebook_instance: NotebookModel) -> None:
        """
        Delete one notebook instance. This assumes that it has been already verified that notebook exists.

        Args:
            notebook_instance: notebook to delete
        """

        exists = self._instance_exists(notebook_instance)
        if exists:
            logger.user_info(
                f"Deleting {self.instance_type} {notebook_instance.name} ..."
            )
            deleted = self.notebook_client.delete_instance(
                name=f"projects/{notebook_instance.project_id}/locations/"
                f"{notebook_instance.zone}/instances/{notebook_instance.name}"
            )
            deleted.result()
            logger.user_success(
                f"Deleted {self.instance_type} {notebook_instance.name}"
            )
        else:
            logger.user_error(
                f"Notebook with name {notebook_instance.name} was not found in region {notebook_instance.region}",
            )
            typer.Exit(1)

    def _create_one_instance(self, instance: NotebookModel, **kwargs) -> None:
        """
        Create a notebook instance based on information in NotebookModel class.
        1. Check if the notebook already exists
        2. Parse the information from NotebookModel to GCP API friendly format = instance_request
        3. Wait for the compute instance behind the notebook to start
        4. Wait for JupyterLab to start
        5. Get and print the link to JupyterLab

        Args:
            instance: notebook to be created

        """
        exists = self._instance_exists(instance)
        if exists:
            logger.user_info(
                f"Instance {instance.name} already exists in location {instance.zone}"
            )
            should_recreate = typer.confirm(
                "Are you sure you want to delete it and start a new?"
            )
            if should_recreate:
                self._delete_one_instance(instance)
            else:
                return
        push_mode: PushMode = kwargs.get("push_mode")  # type: ignore
        instance_request = self._create_instance_request(
            notebook_instance=instance, deploy=True, push_mode=push_mode
        )
        logger.user_info(
            f"Creating underlying compute engine instance for {instance.name} ..."
        )
        nb_instance = self.notebook_client.create_instance(instance_request)
        instance_full_name = (
            nb_instance.result().name
        )  # .result() waits for compute engine behind the notebook to start
        logger.user_info(f"Starting JupyterLab for {instance.name} ...")
        wait(
            lambda: self._validate_jupyterlab_state(
                instance_full_name, Instance.State.ACTIVE
            ),
            timeout_seconds=450,
            sleep_seconds=20,
            waiting_for="Starting JupyterLab in your instance",
        )
        jupyterlab_link = self._get_jupyterlab_link(instance_full_name)
        logger.user_success(
            f"JupyterLab for {instance.name} started at {jupyterlab_link}"
        )

    def _list_running_instances(self, project_id: str, location: str) -> List[str]:
        """
        List all notebooks with given project_id and location.

        Args:
            project_id: GCP project ID
            location: GCP location (zone)

        Returns:
            instance_names: List of the full names on notebook instances (this includes project_id, and zone)

        """
        instances = self.notebook_client.list_instances(
            parent=f"projects/{project_id}/locations/{location}"
        )
        instance_names = [i.name for i in instances.instances]
        return instance_names

    def _instance_exists(self, instance: NotebookModel) -> bool:
        """
        Check if the instance with given instance_name exists in given GCP project project_id and location.
        Args:
            instance: notebook to verify if exists on GCP

        Returns:
            True if exists, False if not
        """
        full_instance_name = f"projects/{instance.project_id}/locations/{instance.zone}/instances/{instance.name}"
        return full_instance_name in self._list_running_instances(
            instance.project_id, instance.zone
        )

    def _create_instance_request(
        self,
        notebook_instance: NotebookModel,
        deploy: bool = True,
        push_mode: PushMode = PushMode.all,
    ) -> CreateInstanceRequest:
        """
        Transform the information about desired notebook from our NotebookModel model (based on yaml config)
        to the form suitable for GCP API.

        Args:
            notebook_instance

        Returns:
            CreateInstanceRequest
        """

        # Network
        full_network_name = self._get_resource_network(
            project_id=self.config.gcp_profile.project_id,
            push_mode=PushMode.all,
            resource_network=notebook_instance.network,
            fallback_project_network=self.config.gcp_profile.network,
            use_project_number=True,
        )
        subnet = (
            notebook_instance.subnet
            if notebook_instance.subnet
            else self.config.gcp_profile.subnet
        )
        full_subnet_name = self._get_resource_subnet(
            full_network_name,
            subnet,
            notebook_instance.region,
        )

        # GPU
        if notebook_instance.gpu:
            accelerator_config = Instance.AcceleratorConfig(
                core_count=notebook_instance.gpu.count,
                type_=notebook_instance.gpu.accelerator_type,
            )
            install_gpu_driver = notebook_instance.gpu.install_gpu_driver
        else:
            accelerator_config = None
            install_gpu_driver = False
        # Environment
        if notebook_instance.environment.docker_image_ref:
            if self.docker_service:
                image_url = self.docker_service.build_container_and_get_image_url(
                    notebook_instance.environment.docker_image_ref, push_mode=push_mode
                )
                repository = image_url.partition(":")[0]
                tag = image_url.partition(":")[-1]
                container_image = ContainerImage(
                    repository=repository,
                    tag=tag,
                )
                vm_image = None
            else:
                raise Exception("Docker params in wanna-ml config not defined")
        elif notebook_instance.environment.vm_image:
            vm_image = VmImage(
                project="deeplearning-platform-release",
                image_family=construct_vm_image_family_from_vm_image(
                    notebook_instance.environment.vm_image.framework,
                    notebook_instance.environment.vm_image.version,
                    notebook_instance.environment.vm_image.os,
                ),
            )
            container_image = None
        else:
            raise ValueError(
                "No notebook environment was found. This should not be possible."
                " Something went wrong during model validation"
            )
        # Disks
        boot_disk_type = (
            notebook_instance.boot_disk.disk_type
            if notebook_instance.boot_disk
            else None
        )
        boot_disk_size_gb = (
            notebook_instance.boot_disk.size_gb if notebook_instance.boot_disk else None
        )
        data_disk_type = (
            notebook_instance.data_disk.disk_type
            if notebook_instance.data_disk
            else None
        )
        data_disk_size_gb = (
            notebook_instance.data_disk.size_gb if notebook_instance.data_disk else None
        )
        disk_encryption = "CMEK" if self.config.gcp_profile.kms_key else None
        kms_key = (
            self.config.gcp_profile.kms_key if self.config.gcp_profile.kms_key else None
        )

        # service account and instance owners
        service_account = notebook_instance.service_account
        instance_owner = self.owner or notebook_instance.owner
        instance_owners = [instance_owner] if instance_owner else None

        # labels and tags
        tags = notebook_instance.tags
        labels = {
            "wanna_name": notebook_instance.name,
            "wanna_resource": self.instance_type,
        }
        if instance_owner:
            labels["wanna_owner"] = email_fixer(instance_owner)
        if notebook_instance.labels:
            labels = {**notebook_instance.labels, **labels}

        # post startup script
        if deploy and (
            notebook_instance.bucket_mounts
            or notebook_instance.tensorboard_ref
            or notebook_instance.idle_shutdown_timeout
            or self.config.gcp_profile.env_vars
            or notebook_instance.env_vars
        ):
            script = self._prepare_startup_script(self.instances[0])
            blob = upload_string_to_gcs(
                script,
                notebook_instance.bucket or self.bucket_name,
                f"notebooks/{notebook_instance.name}/startup_script.sh",
            )
            post_startup_script = f"gs://{blob.bucket.name}/{blob.name}"
        else:
            post_startup_script = None

        metadata = notebook_instance.metadata or {}
        if notebook_instance.enable_monitoring:
            enable_monitoring_metadata = {
                "enable-guest-attributes": "TRUE",
                "report-system-health": "TRUE",
                "report-notebook-metrics": "TRUE",
                "install-monitoring-agent": "TRUE",
                "enable-extended-ui": "TRUE",
            }
            metadata = {**metadata, **enable_monitoring_metadata}
        if notebook_instance.collaborative:
            collaborative_metadata = {"use-collaborative": "TRUE"}
            metadata = {**metadata, **collaborative_metadata}
        if notebook_instance.backup:
            backup_metadata = {"gcs-data-bucket": notebook_instance.backup}
            metadata = {**metadata, **backup_metadata}

        instance = Instance(
            vm_image=vm_image,
            container_image=container_image,
            machine_type=notebook_instance.machine_type,
            accelerator_config=accelerator_config,
            install_gpu_driver=install_gpu_driver,
            network=full_network_name,
            subnet=full_subnet_name,
            boot_disk_type=boot_disk_type,
            boot_disk_size_gb=boot_disk_size_gb,
            data_disk_type=data_disk_type,
            data_disk_size_gb=data_disk_size_gb,
            post_startup_script=post_startup_script,
            instance_owners=instance_owners,
            service_account=service_account,
            metadata=metadata,
            tags=tags,
            labels=labels,
            disk_encryption=disk_encryption,
            kms_key=kms_key,
            no_public_ip=notebook_instance.no_public_ip,
            no_proxy_access=notebook_instance.no_proxy_access,
        )

        return CreateInstanceRequest(
            parent=f"projects/{notebook_instance.project_id}/locations/{notebook_instance.zone}",
            instance_id=notebook_instance.name,
            instance=instance,
        )

    def _prepare_startup_script(self, nb_instance: NotebookModel) -> str:
        """
        Prepare the notebook startup script based on the information from notebook.
        This script run at the Compute Engine Instance creation time with a root user.

        Args:
            nb_instance

        Returns:
            startup_script
        """
        env_vars = (
            self.config.gcp_profile.env_vars
            if self.config.gcp_profile.env_vars
            else dict()
        )
        if nb_instance.env_vars:
            env_vars = {**env_vars, **nb_instance.env_vars}

        if nb_instance.tensorboard_ref:
            tensorboard_resource_name = (
                self.tensorboard_service.get_or_create_tensorboard_instance_by_name(
                    nb_instance.tensorboard_ref
                )
            )
        else:
            tensorboard_resource_name = None

        startup_script = templates.render_template(
            Path("notebook_startup_script.sh.j2"),
            bucket_mounts=nb_instance.bucket_mounts,
            tensorboard_resource_name=tensorboard_resource_name,
            idle_shutdown_timeout=nb_instance.idle_shutdown_timeout,
            env_vars=env_vars,
        )
        return startup_script

    def _validate_jupyterlab_state(self, instance_id: str, state: int) -> bool:
        """
        Validate if the given notebook instance is in given state.

        Args:
            instance_id: Full notebook instance id
            state: Notebook state (ACTIVE, PENDING,...)

        Returns:
            True if desired state, False otherwise
        """
        try:
            instance_info = self.notebook_client.get_instance(name=instance_id)
        except exceptions.NotFound:
            raise exceptions.NotFound(
                f"Notebook {instance_id} was not found."
            ) from None
        return instance_info.state == state

    def _get_jupyterlab_link(self, instance_id: str) -> str:
        """
        Get a link to jupyterlab proxy based on given notebook instance id.
        Args:
            instance_id: full notebook instance id

        Returns:
            proxy_uri: link to jupyterlab
        """
        instance_info = self.notebook_client.get_instance({"name": instance_id})
        return f"https://{instance_info.proxy_uri}"

    def _ssh(
        self, notebook_instance: NotebookModel, run_in_background: bool, local_port: int
    ) -> None:
        """
        SSH connect to the notebook instance if the instance is already started.

        Args:
            notebook_instance: notebook model representing the instance you want to connect to
            run_in_background: whether to run in the background or in interactive mode
            local_port: jupyter lab will be exposed at this port at localhost

        Returns:

        """
        exists = self._instance_exists(notebook_instance)
        if not exists:
            logger.user_info(
                f"Notebook {notebook_instance.name} is not running, create it first and then ssh connect to it."
            )
            return

        bash_command = f"gcloud compute ssh \
             --project {notebook_instance.project_id} \
             --zone {notebook_instance.zone} \
             --tunnel-through-iap \
              {notebook_instance.name} \
             -- -L 8080:localhost:{local_port}"
        if run_in_background:
            bash_command += " -N -f"

        process = subprocess.Popen(bash_command.split())
        process.communicate()

    def ssh(self, instance_name: str, run_in_background: bool, local_port: int) -> None:
        """
        A wrapper around _ssh method, but this function also verifies if the notebook is
        defined in YAML config and already started.

        Args:
            instance_name: name of the notebook to connect to
            run_in_background: whether to run in the background or in interactive mode
            local_port: jupyter lab will be exposed at this port at localhost

        Returns:

        """
        if instance_name == "all":
            if len(self.config.notebooks) == 1:
                self._ssh(self.config.notebooks[0], run_in_background, local_port)
            elif len(self.config.notebooks) > 1:
                raise ValueError("You can connect to only one notebook at a time.")
            else:
                logger.user_error("No notebook definition found in your YAML config.")
        else:
            if instance_name in [notebook.name for notebook in self.config.notebooks]:
                self._ssh(
                    [
                        notebook
                        for notebook in self.config.notebooks
                        if notebook.name == instance_name
                    ][0],
                    run_in_background,
                    local_port,
                )
            else:
                logger.user_error(f"No notebook {instance_name} found")
                raise ValueError(
                    f"Notebook {instance_name} does not exists in configuration"
                )

    def build(self) -> int:
        for instance in self.instances:
            self._create_instance_request(
                notebook_instance=instance, deploy=False, push_mode=PushMode.manifests
            )
        logger.user_success("Notebooks validation OK!")
        return 0

    def push(self, instance_name: str):
        instances = self._filter_instances_by_name(instance_name)

        docker_image_refs = set(
            [
                instance.environment.docker_image_ref
                for instance in instances
                if instance.environment.docker_image_ref
            ]
        )
        if docker_image_refs:
            if self.docker_service:
                for docker_image_ref in docker_image_refs:
                    image_tag = self.docker_service.get_image(
                        docker_image_ref=docker_image_ref
                    )
                    if image_tag[1]:
                        self.docker_service.push_image(image_tag[1])
            else:
                raise Exception("Docker params in wanna-ml config not defined")

    def _return_diff(self) -> Tuple[List[NotebookModel], List[NotebookModel]]:
        """
        Figuring out the diff between GCP and wanna.yaml. Lists user-managed notebooks to be deleted and created.
        """
        # We list compute instances and not notebooks, because with notebooks you cannot list instances in all zones.
        # So instead we list all Compute Engine instances with notebook labels
        instance_client = compute_v1.InstancesClient()
        request = compute_v1.AggregatedListInstancesRequest(
            filter=f"(labels.wanna_resource:notebook) (labels.wanna_project:{self.wanna_project.name})"
        )
        request.project = self.config.gcp_profile.project_id
        agg_list = instance_client.aggregated_list(request=request)
        gcp_instances = itertools.chain(
            *[resp.instances for zone, resp in agg_list if resp.instances]
        )

        active_notebooks = [
            NotebookModel.parse_obj(
                {
                    "name": i.name,
                    "zone": i.zone.split("/")[-1],
                    "project_id": self.config.gcp_profile.project_id,
                }
            )
            for i in gcp_instances
        ]
        active_notebook_names = [n.name for n in active_notebooks]
        wanna_notebook_names = [n.name for n in self.instances]

        to_be_deleted = []
        to_be_created = []
        """
        Notebooks to be deleted
        """
        for active_notebook in active_notebooks:
            if active_notebook.name not in wanna_notebook_names:
                to_be_deleted.append(active_notebook)
        """
        Notebooks to be created
        """
        for wanna_notebook in self.instances:
            if wanna_notebook.name not in active_notebook_names:
                to_be_created.append(wanna_notebook)
        return to_be_deleted, to_be_created
