import subprocess
from pathlib import Path
from typing import List, Optional

import typer
from google.api_core import exceptions
from google.cloud.notebooks_v1.services.managed_notebook_service import ManagedNotebookServiceClient
from google.cloud.notebooks_v1.services.notebook_service import NotebookServiceClient
from google.cloud.notebooks_v1.types import (
    ContainerImage,
    CreateInstanceRequest,
    CreateRuntimeRequest,
    Instance,
    LocalDisk,
    LocalDiskInitializeParams,
    Runtime,
    RuntimeAcceleratorConfig,
    RuntimeAccessConfig,
    RuntimeSoftwareConfig,
    VirtualMachine,
    VirtualMachineConfig,
    VmImage,
)
from waiting import wait

from wanna.core.loggers.wanna_logger import get_logger
from wanna.core.models.notebook import ManagedNotebookModel, NotebookModel
from wanna.core.models.wanna_config import WannaConfigModel
from wanna.core.services.base import BaseService
from wanna.core.services.docker import DockerService
from wanna.core.services.tensorboard import TensorboardService
from wanna.core.utils import templates
from wanna.core.utils.gcp import construct_vm_image_family_from_vm_image, upload_string_to_gcs

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

    def _delete_one_instance(self, notebook_instance: NotebookModel) -> None:
        """
        Delete one notebook instance. This assumes that it has been already verified that notebook exists.

        Args:
            notebook_instance: notebook to delete
        """

        exists = self._instance_exists(notebook_instance)
        if exists:
            with logger.user_spinner(f"Deleting {self.instance_type} {notebook_instance.name}"):
                deleted = self.notebook_client.delete_instance(
                    name=f"projects/{notebook_instance.project_id}/locations/"
                    f"{notebook_instance.zone}/instances/{notebook_instance.name}"
                )
                deleted.result()
        else:
            logger.user_error(
                f"Notebook with name {notebook_instance.name} was not found in region {notebook_instance.region}",
            )

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
            logger.user_info(f"Instance {instance.name} already exists in location {instance.zone}")
            should_recreate = typer.confirm("Are you sure you want to delete it and start a new?")
            if should_recreate:
                self._delete_one_instance(instance)
            else:
                return
        instance_request = self._create_instance_request(notebook_instance=instance, deploy=True)
        with logger.user_spinner(f"Creating underlying compute engine instance for {instance.name}"):
            nb_instance = self.notebook_client.create_instance(instance_request)
            instance_full_name = (
                nb_instance.result().name
            )  # .result() waits for compute engine behind the notebook to start
        with logger.user_spinner("Starting JupyterLab"):
            wait(
                lambda: self._validate_jupyterlab_state(instance_full_name, Instance.State.ACTIVE),
                timeout_seconds=450,
                sleep_seconds=20,
                waiting_for="Starting JupyterLab in your instance",
            )
            jupyterlab_link = self._get_jupyterlab_link(instance_full_name)
        logger.user_success(f"JupyterLab started at {jupyterlab_link}")

    def _list_running_instances(self, project_id: str, location: str) -> List[str]:
        """
        List all notebooks with given project_id and location.

        Args:
            project_id: GCP project ID
            location: GCP location (zone)

        Returns:
            instance_names: List of the full names on notebook instances (this includes project_id, and zone)

        """
        instances = self.notebook_client.list_instances(parent=f"projects/{project_id}/locations/{location}")
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
        return full_instance_name in self._list_running_instances(instance.project_id, instance.zone)

    def _create_instance_request(self, notebook_instance: NotebookModel, deploy: bool = True) -> CreateInstanceRequest:
        """
        Transform the information about desired notebook from our NotebookModel model (based on yaml config)
        to the form suitable for GCP API.

        Args:
            notebook_instance

        Returns:
            CreateInstanceRequest
        """
        # Network
        if notebook_instance.network:
            full_network_name = f"projects/{notebook_instance.project_id}/global/networks/{notebook_instance.network}"
        else:
            full_network_name = None

        if notebook_instance.subnet:
            full_subnet_name = (
                f"projects/{notebook_instance.project_id}/region/"
                f"{notebook_instance.zone}/subnetworks/{notebook_instance.subnet}"
            )
        else:
            full_subnet_name = None

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
                vm_image = None
                image_tag = self.docker_service.get_image(
                    docker_image_ref=notebook_instance.environment.docker_image_ref
                )
                if image_tag[1]:
                    self.docker_service.push_image(image_tag[1])
                repository = image_tag[2].partition(":")[0]
                tag = image_tag[2].partition(":")[-1]
                container_image = ContainerImage(
                    repository=repository,
                    tag=tag,
                )
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
        boot_disk_type = notebook_instance.boot_disk.disk_type if notebook_instance.boot_disk else None
        boot_disk_size_gb = notebook_instance.boot_disk.size_gb if notebook_instance.boot_disk else None
        data_disk_type = notebook_instance.data_disk.disk_type if notebook_instance.data_disk else None
        data_disk_size_gb = notebook_instance.data_disk.size_gb if notebook_instance.data_disk else None

        # service account and instance owners
        service_account = notebook_instance.service_account
        instance_owner = self.owner or notebook_instance.instance_owner
        instance_owners = [instance_owner] if instance_owner else None

        # labels and tags
        tags = notebook_instance.tags
        labels = {
            "wanna_name": notebook_instance.name,
            "wanna_resource": self.instance_type,
        }
        if notebook_instance.labels:
            labels = {**notebook_instance.labels, **labels}

        # post startup script
        if deploy and (notebook_instance.bucket_mounts or notebook_instance.tensorboard_ref):
            script = self._prepare_startup_script(self.instances[0])
            blob = upload_string_to_gcs(
                script,
                notebook_instance.bucket or self.bucket_name,
                f"notebooks/{notebook_instance.name}/startup_script.sh",
            )
            post_startup_script = f"gs://{blob.bucket.name}/{blob.name}"
        else:
            post_startup_script = None

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
            tags=tags,
            labels=labels,
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
        bucket_mounts = nb_instance.bucket_mounts
        if nb_instance.tensorboard_ref:
            tensorboard_resource_name = self.tensorboard_service.get_or_create_tensorboard_instance_by_name(
                nb_instance.tensorboard_ref
            )
        else:
            tensorboard_resource_name = None
        startup_script = templates.render_template(
            Path("notebook_startup_script.sh.j2"),
            bucket_mounts=bucket_mounts,
            tensorboard_resource_name=tensorboard_resource_name,
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
            raise exceptions.NotFound(f"Notebook {instance_id} was not found.") from None
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

    def _ssh(self, notebook_instance: NotebookModel, run_in_background: bool, local_port: int) -> None:
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
                Exception("You can connect to only one notebook at a time.")
            else:
                logger.user_error("No notebook definition found in your YAML config.")
        else:
            if instance_name in [notebook.name for notebook in self.config.notebooks]:
                self._ssh(
                    [notebook for notebook in self.config.notebooks if notebook.name == instance_name][0],
                    run_in_background,
                    local_port,
                )
            else:
                logger.user_error(f"No notebook {instance_name} found")

    def build(self) -> int:
        for instance in self.instances:
            self._create_instance_request(notebook_instance=instance, deploy=False)
        logger.user_success("Notebooks validation OK!")
        return 0


class ManagedNotebookService(BaseService[ManagedNotebookModel]):
    def __init__(
        self,
        config: WannaConfigModel,
        workdir: Path,
        version: str = "dev",
    ):
        super().__init__(
            instance_type="managed-notebook",
        )
        self.version = version
        self.instances = config.managed_notebooks
        self.notebook_client = ManagedNotebookServiceClient()
        self.config = config
        self.bucket_name = config.gcp_profile.bucket
        self.tensorboard_service = TensorboardService(config=config)

    def _create_runtime_request(self, instance: ManagedNotebookModel, deploy: bool = True) -> CreateRuntimeRequest:
        """
        Transform the information about desired managed-notebook from the model based on yaml config
        to the form suitable for GCP API.

        Args:
            instance

        Returns:
            CreateRuntimeRequest
        """
        # Configuration of the managed notebook
        labels = {
            "wanna_name": instance.name,
            "wanna_resource": self.instance_type,
        }
        if instance.labels:
            labels = {**instance.labels, **labels}
        # Disks
        disk_type = instance.data_disk.disk_type if instance.data_disk else None
        disk_size_gb = instance.data_disk.size_gb if instance.data_disk else None
        localDiskParams = LocalDiskInitializeParams(disk_size_gb=disk_size_gb, disk_type=disk_type)
        localDisk = LocalDisk(initialize_params=localDiskParams)
        # Accelerator
        if instance.gpu:
            runtimeAcceleratorConfig = RuntimeAcceleratorConfig(
                type=instance.gpu.accelerator_type, core_count=instance.gpu.count
            )
        else:
            runtimeAcceleratorConfig = None
        # Network and subnetwork
        if instance.subnet:
            full_network = f"projects/{instance.project_id}/regions/global/{instance.network}"
            full_subnet = f"projects/{instance.project_id}/regions/{instance.region}/subnetworks/{instance.subnet}"
        else:
            full_network = None
            full_subnet = None

        # Post startup script
        if deploy and instance.tensorboard_ref:
            script = self._prepare_startup_script(self.instances[0])
            blob = upload_string_to_gcs(
                script,
                instance.bucket or self.bucket_name,
                f"notebooks/{instance.name}/startup_script.sh",
            )
            post_startup_script = f"gs://{blob.bucket.name}/{blob.name}"
        else:
            post_startup_script = None

        # VM
        virtualMachineConfig = VirtualMachineConfig(
            machine_type=instance.machine_type,
            data_disk=localDisk,
            labels=labels,
            accelerator_config=runtimeAcceleratorConfig,
            network=full_network,
            subnet=full_subnet,
            # internal_ip_only=instance.internal_ip_only,
            tags=instance.tags,
            metadata=instance.metadata,
        )
        virtualMachine = VirtualMachine(virtual_machine_config=virtualMachineConfig)
        # Runtime
        runtimeSoftwareConfig = RuntimeSoftwareConfig(
            {
                "kernels": instance.kernels,
                "post_startup_script": post_startup_script,
                "idle_shutdown": instance.idle_shutdown,
                "idle_shutdown_timeout": instance.idle_shutdown_timeout,
            }
        )
        runtimeAccessConfig = RuntimeAccessConfig(
            access_type=RuntimeAccessConfig.RuntimeAccessType.SINGLE_USER, runtime_owner=instance.owner
        )
        runtime = Runtime(
            access_config=runtimeAccessConfig, software_config=runtimeSoftwareConfig, virtual_machine=virtualMachine
        )
        # Create runtime request
        return CreateRuntimeRequest(
            parent=f"projects/{instance.project_id}/locations/{instance.region}",
            runtime_id=instance.name,
            runtime=runtime,
        )

    def _delete_one_instance(self, notebook_instance: ManagedNotebookModel) -> None:
        """
        Delete one notebook instance. This assumes that it has been already verified that notebook exists.

        Args:
            notebook_instance: notebook to delete
        """

        exists = self._instance_exists(notebook_instance)
        if exists:
            with logger.user_spinner(f"Deleting {self.instance_type} {notebook_instance.name}"):
                deleted = self.notebook_client.delete_runtime(
                    name=f"projects/{notebook_instance.project_id}/locations/"
                    f"{notebook_instance.region}/runtimes/{notebook_instance.name}"
                )
                deleted.result()
        else:
            logger.user_error(
                f"Notebook with name {notebook_instance.name} was not found in region {notebook_instance.region}",
            )

    def _create_one_instance(self, instance: ManagedNotebookModel, **kwargs) -> None:
        """
        Create a notebook instance based on information in NotebookModel class.
        1. Check if the notebook already exists
        2. Parse the information from NotebookModel to GCP API friendly format = runtime_request
        3. Wait for the compute instance behind the notebook to start
        4. Wait for JupyterLab to start
        5. Get and print the link to JupyterLab

        Args:
            instance: notebook to be created

        """
        exists = self._instance_exists(instance)
        if exists:
            logger.user_info(f"Managed notebook {instance.name} already exists in location {instance.region}")
            should_recreate = typer.confirm("Are you sure you want to delete it and start a new?")
            if should_recreate:
                self._delete_one_instance(instance)
            else:
                return

        request = self._create_runtime_request(instance=instance, deploy=True)
        with logger.user_spinner(f"Creating underlying compute engine instance for {instance.name}"):
            nb_instance = self.notebook_client.create_runtime(request=request)
            instance_full_name = (
                nb_instance.result().name
            )  # .result() waits for compute engine behind the notebook to start
        with logger.user_spinner("Starting JupyterLab"):
            wait(
                lambda: self._validate_jupyterlab_state(instance_full_name, Runtime.State.ACTIVE),
                timeout_seconds=450,
                sleep_seconds=20,
                waiting_for="Starting JupyterLab in your instance",
            )
            jupyterlab_link = self._get_jupyterlab_link(instance_full_name)
        logger.user_success(f"JupyterLab started at {jupyterlab_link}")

    def _list_running_instances(self, project_id: str, location: str) -> List[str]:
        """
        List all notebooks with given project_id and location.

        Args:
            project_id: GCP project ID
            location: GCP location (zone)

        Returns:
            instance_names: List of the full names on notebook instances (this includes project_id, and zone)

        """
        instances = self.notebook_client.list_runtimes(parent=f"projects/{project_id}/locations/{location}")
        instance_names = [i.name for i in instances.runtimes]
        return instance_names

    def _instance_exists(self, instance: ManagedNotebookModel) -> bool:
        """
        Check if the instance with given instance_name exists in given GCP project project_id and location.
        Args:
            instance: notebook to verify if exists on GCP

        Returns:
            True if exists, False if not
        """
        full_instance_name = f"projects/{instance.project_id}/locations/{instance.region}/runtimes/{instance.name}"
        return full_instance_name in self._list_running_instances(
            instance.project_id, instance.region or self.config.gcp_profile.region
        )

    def _prepare_startup_script(self, nb_instance: ManagedNotebookModel) -> str:
        """
        Prepare the notebook startup script based on the information from notebook.
        This script run at the Compute Engine Instance creation time with a root user.

        Args:
            nb_instance

        Returns:
            startup_script
        """
        if nb_instance.tensorboard_ref:
            tensorboard_resource_name = self.tensorboard_service.get_or_create_tensorboard_instance_by_name(
                nb_instance.tensorboard_ref
            )
        else:
            tensorboard_resource_name = None
        startup_script = templates.render_template(
            Path("notebook_startup_script.sh.j2"),
            tensorboard_resource_name=tensorboard_resource_name,
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
            instance_info = self.notebook_client.get_runtime(name=instance_id)
        except exceptions.NotFound:
            raise exceptions.NotFound(f"Managed Notebook {instance_id} was not found.") from None
        return instance_info.state == state

    def _get_jupyterlab_link(self, instance_id: str) -> str:
        """
        Get a link to jupyterlab proxy based on given notebook instance id.
        Args:
            instance_id: full notebook instance id

        Returns:
            proxy_uri: link to jupyterlab
        """
        instance_info = self.notebook_client.get_runtime({"name": instance_id})
        return f"https://{instance_info.access_config.proxy_uri}"

    def _return_diff(self):
        """
        Figuring out the diff between GCP and wanna.yaml. Lists managed notebooks to be deleted and created.
        """
        parent = f"projects/{self.config.gcp_profile.project_id}/locations/{self.config.gcp_profile.region}"
        active_runtimes = self.notebook_client.list_runtimes(parent=parent)
        wanna_names = [managednotebook.name for managednotebook in self.instances]
        existing_names = [runtime.name for runtime in active_runtimes]
        to_be_deleted = []
        to_be_created = []
        """
        Notebooks to be deleted
        """
        for runtime in active_runtimes:
            if runtime.virtual_machine.virtual_machine_config.labels["wanna_project"] == self.config.wanna_project.name:
                if runtime.name.split("/")[-1] not in wanna_names:
                    to_be_deleted.append(runtime.name)
        """
        Notebooks to be created
        """
        for notebook in self.instances:
            if (
                f"projects/{notebook.project_id}/locations/{notebook.region}/runtimes/{notebook.name}"
                not in existing_names
            ):
                to_be_created.append(notebook)
        return to_be_deleted, to_be_created

    def sync(self) -> None:
        """
        1. Reads current notebooks where label is defined per field wanna_project.name in wanna.yaml
        2. Does a diff between what is on GCP and what is on yaml
        3. Delete the ones in GCP that are not in wanna.yaml
        4. Create the ones defined in yaml and missing in GCP
        """
        to_be_deleted, to_be_created = self._return_diff()

        if to_be_deleted:
            to_be_deleted_str = "\n".join(["-" + item for item in to_be_deleted])
            logger.info(
                f"Managed notebooks to be deleted:\n{to_be_deleted_str}",
            )
            should_delete = typer.confirm("Are you sure you want to delete them?")
            if should_delete:
                for item in to_be_deleted:
                    with logger.user_spinner(f"Deleting {item}"):
                        deleted = self.notebook_client.delete_runtime(name=item)
                        deleted.result()
            else:
                return

        if to_be_created:
            to_be_created_str = "\n".join(["-" + item.name for item in to_be_created])
            logger.user_info(f"Managed notebooks to be created:\n{to_be_created_str}")
            should_create = typer.confirm("Are you sure you want to create them?")
            if should_create:
                for item in to_be_created:
                    self._create_one_instance(item)
            else:
                return

        logger.user_success("Managed notebooks on GCP are in sync with wanna.yaml")

    def build(self) -> int:
        for instance in self.instances:
            self._create_runtime_request(instance=instance, deploy=False)
        logger.user_success("Managed notebooks validation OK!")
        return 0
