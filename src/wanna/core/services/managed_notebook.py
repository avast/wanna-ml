import itertools
from pathlib import Path

import typer
from google.api_core import exceptions
from google.api_core.operation import Operation
from google.cloud.notebooks_v1.services.managed_notebook_service import (
    ManagedNotebookServiceClient,
)
from google.cloud.notebooks_v1.types import (
    ContainerImage,
    CreateRuntimeRequest,
    EncryptionConfig,
    LocalDisk,
    LocalDiskInitializeParams,
    Runtime,
    RuntimeAcceleratorConfig,
    RuntimeAccessConfig,
    RuntimeSoftwareConfig,
    VirtualMachine,
    VirtualMachineConfig,
)
from waiting import wait

from wanna.core.deployment.models import PushMode
from wanna.core.loggers.wanna_logger import get_logger
from wanna.core.models.wanna_config import WannaConfigModel
from wanna.core.models.workbench import BaseWorkbenchModel, ManagedNotebookModel
from wanna.core.services.docker import DockerService
from wanna.core.services.tensorboard import TensorboardService
from wanna.core.services.workbench import BaseWorkbenchService, CreateRequest, Instances
from wanna.core.utils import templates
from wanna.core.utils.config_enricher import email_fixer
from wanna.core.utils.gcp import upload_string_to_gcs

logger = get_logger(__name__)


class ManagedNotebookService(BaseWorkbenchService[ManagedNotebookModel]):
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
        self.docker_service = (
            DockerService(
                docker_model=config.docker,
                gcp_profile=config.gcp_profile,
                version=version,
                work_dir=workdir,
                wanna_project_name=config.wanna_project.name,
            )
            if config.docker
            else None
        )

    def _create_instance_request(
        self,
        instance: ManagedNotebookModel,
        deploy: bool = True,
        push_mode: PushMode = PushMode.all,
    ) -> CreateRuntimeRequest:
        # Configuration of the managed notebook
        labels = {
            "wanna_name": instance.name,
            "wanna_resource": self.instance_type,
        }

        notebook_owner = instance.owner or self.config.gcp_profile.service_account

        if notebook_owner:
            labels["wanna_owner"] = email_fixer(notebook_owner)
            access_type = (
                RuntimeAccessConfig.RuntimeAccessType.SERVICE_ACCOUNT
                if notebook_owner.endswith("gserviceaccount.com")
                else RuntimeAccessConfig.RuntimeAccessType.SINGLE_USER
            )
        else:
            access_type = None

        if instance.labels:
            labels = {**instance.labels, **labels}

        # Disks
        disk_type = instance.data_disk.disk_type if instance.data_disk else None
        disk_size_gb = instance.data_disk.size_gb if instance.data_disk else None
        local_disk_params = LocalDiskInitializeParams(disk_size_gb=disk_size_gb, disk_type=disk_type)
        local_disk = LocalDisk(initialize_params=local_disk_params)
        encryption_config = (
            EncryptionConfig(kms_key=self.config.gcp_profile.kms_key) if self.config.gcp_profile.kms_key else None
        )

        # Accelerator
        if instance.gpu:
            runtimeAcceleratorConfig = RuntimeAcceleratorConfig(
                type=instance.gpu.accelerator_type, core_count=instance.gpu.count
            )
        else:
            runtimeAcceleratorConfig = None

        # Network and subnetwork
        full_network = self._get_resource_network(
            project_id=self.config.gcp_profile.project_id,
            push_mode=PushMode.all,
            resource_network=instance.network,
            fallback_project_network=self.config.gcp_profile.network,
            use_project_number=False,
        )
        subnet = instance.subnet if instance.subnet else self.config.gcp_profile.subnet
        full_subnet = self._get_resource_subnet(
            full_network,
            subnet,
            self.workbench_location(instance),
        )

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

        # Runtime kernels
        kernels = []
        if instance.kernel_docker_image_refs:
            if not self.docker_service:
                raise Exception("Docker params in wanna-ml config not defined")
            for docker_image_ref in instance.kernel_docker_image_refs:
                image_url = self.docker_service.build_container_and_get_image_url(docker_image_ref, push_mode=push_mode)
                repository = image_url.partition(":")[0]
                tag = image_url.partition(":")[-1]
                kernels.append(ContainerImage(repository=repository, tag=tag))

        # VM
        virtualMachineConfig = VirtualMachineConfig(
            machine_type=instance.machine_type,
            container_images=kernels,
            data_disk=local_disk,
            encryption_config=encryption_config,
            accelerator_config=runtimeAcceleratorConfig,
            network=full_network,
            subnet=full_subnet,
            internal_ip_only=instance.internal_ip_only,
            tags=instance.tags,
            # Currently creating managed notebooks with metadata or labels fails
            # we need to disable this for the time being, until labels is added Runtime proto
            # as it's now available on the rest interface
            # metadata=instance.metadata,
            # labels=labels,
        )
        virtualMachine = VirtualMachine(virtual_machine_config=virtualMachineConfig)

        runtimeSoftwareConfig = RuntimeSoftwareConfig(
            {
                "post_startup_script": post_startup_script,
                "idle_shutdown": instance.idle_shutdown,
                "idle_shutdown_timeout": instance.idle_shutdown_timeout,
                "enable_health_monitoring": True,
            }
        )

        runtimeAccessConfig = RuntimeAccessConfig(access_type=access_type, runtime_owner=notebook_owner)
        runtime = Runtime(
            access_config=runtimeAccessConfig,
            software_config=runtimeSoftwareConfig,
            virtual_machine=virtualMachine,
        )

        # Create runtime request
        return CreateRuntimeRequest(
            parent=f"projects/{instance.project_id}/locations/{self.workbench_location(instance)}",
            runtime_id=instance.name,
            runtime=runtime,
        )

    def _delete_instance_client(self, instance: ManagedNotebookModel) -> Operation:
        return self.notebook_client.delete_runtime(
            name=f"projects/{instance.project_id}/locations/"
            f"{self.workbench_location(instance)}/runtimes/{instance.name}"
        )

    def _create_instance_client(self, request: CreateRuntimeRequest) -> Operation:
        return self.notebook_client.create_runtime(request=request)

    def workbench_location(self, instance: ManagedNotebookModel) -> str:
        return instance.region or self.config.gcp_profile.region

    def _list_running_instances(self, project_id: str, location: str) -> list[str]:
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
        full_instance_name = (
            f"projects/{instance.project_id}/locations/{self.workbench_location(instance)}/runtimes/{instance.name}"
        )
        return full_instance_name in self._list_running_instances(
            instance.project_id, self.workbench_location(instance)
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

    def _client_get_instance(self, instance_id: str) -> Instances:
        return self.notebook_client.get_runtime(name=instance_id)

    def _get_jupyterlab_link(self, instance_id: str) -> str:
        instance_info = self.notebook_client.get_runtime({"name": instance_id})
        return f"https://{instance_info.access_config.proxy_uri}"

    def _return_diff(
        self,
    ) -> tuple[list[ManagedNotebookModel], list[ManagedNotebookModel]]:
        """
        Figuring out the diff between GCP and wanna.yaml. Lists managed notebooks to be deleted and created.
        """
        location = self.config.gcp_profile.region
        parent = f"projects/{self.config.gcp_profile.project_id}/locations/{location}"
        active_runtimes = self.notebook_client.list_runtimes(parent=parent).runtimes
        wanna_notebook_names = [managednotebook.name for managednotebook in self.instances]
        active_notebook_names = [str(runtime.name) for runtime in active_runtimes]
        to_be_deleted = []
        to_be_created = []
        """
        Notebooks to be deleted
        """
        for runtime in active_runtimes:
            if runtime.virtual_machine.virtual_machine_config.labels["wanna_project"] == self.config.wanna_project.name:
                if runtime.name.split("/")[-1] not in wanna_notebook_names:
                    to_be_deleted.append(
                        ManagedNotebookModel.parse_obj(
                            {
                                "name": str(runtime.name).split("/")[-1],
                                "region": location,
                                "project_id": self.config.gcp_profile.project_id,
                                "owner": "wanna-to-be-deleted",
                            }
                        )
                    )
        """
        Notebooks to be created
        """
        for notebook in self.instances:
            if (
                f"projects/{notebook.project_id}/locations/{notebook.region}/runtimes/{notebook.name}"
                not in active_notebook_names
            ):
                to_be_created.append(notebook)

        return to_be_deleted, to_be_created

    def build(self) -> int:
        for instance in self.instances:
            self._create_instance_request(instance=instance, deploy=False, push_mode=PushMode.manifests)
        logger.user_success("Managed notebooks validation OK!")
        return 0

    def push(self, instance_name: str):
        instances = self._filter_instances_by_name(instance_name)

        docker_image_refs = set(
            itertools.chain(
                *[instance.kernel_docker_image_refs for instance in instances if instance.kernel_docker_image_refs]
            )
        )
        if docker_image_refs:
            if self.docker_service:
                for docker_image_ref in docker_image_refs:
                    image_tag = self.docker_service.get_image(docker_image_ref=docker_image_ref)
                    if image_tag[1]:
                        self.docker_service.push_image(image_tag[1])
            else:
                raise Exception("Docker params in wanna-ml config not defined")
