import itertools
import subprocess
from pathlib import Path
from typing import Optional

from google.api_core import exceptions
from google.api_core.operation import Operation
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
from wanna.core.models.workbench import NotebookModel
from wanna.core.models.wanna_config import WannaConfigModel
from wanna.core.services.docker import DockerService
from wanna.core.services.tensorboard import TensorboardService
from wanna.core.services.workbench import BaseWorkbenchService, CreateRequest, Instances
from wanna.core.utils import templates
from wanna.core.utils.config_enricher import email_fixer
from wanna.core.utils.gcp import (
    construct_vm_image_family_from_vm_image,
    upload_string_to_gcs,
)

logger = get_logger(__name__)


class NotebookService(BaseWorkbenchService[NotebookModel]):
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

    def _delete_instance_client(self, instance: NotebookModel) -> Operation:
        return self.notebook_client.delete_instance(
            name=f"projects/{instance.project_id}/locations/"
                 f"{instance.zone}/instances/{instance.name}"
        )

    def _create_instance_client(self, request: CreateInstanceRequest) -> Operation:
        return self.notebook_client.create_instance(request)

    def workbench_location(self, instance: NotebookModel) -> str:
        return instance.zone

    def _list_running_instances(self, project_id: str, location: str) -> list[str]:
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
        full_instance_name = f"projects/{instance.project_id}/locations/{instance.zone}/instances/{instance.name}"
        return full_instance_name in self._list_running_instances(
            instance.project_id, instance.zone
        )

    def _create_instance_request(
        self,
        instance: NotebookModel,
        deploy: bool = True,
        push_mode: PushMode = PushMode.all,
    ) -> CreateInstanceRequest:
        # Network
        full_network_name = self._get_resource_network(
            project_id=self.config.gcp_profile.project_id,
            push_mode=PushMode.all,
            resource_network=instance.network,
            fallback_project_network=self.config.gcp_profile.network,
            use_project_number=True,
        )
        subnet = (
            instance.subnet
            if instance.subnet
            else self.config.gcp_profile.subnet
        )
        full_subnet_name = self._get_resource_subnet(
            full_network_name,
            subnet,
            instance.region,
        )

        # GPU
        if instance.gpu:
            accelerator_config = Instance.AcceleratorConfig(
                core_count=instance.gpu.count,
                type_=instance.gpu.accelerator_type,
            )
            install_gpu_driver = instance.gpu.install_gpu_driver
        else:
            accelerator_config = None
            install_gpu_driver = False
        # Environment
        if instance.environment.docker_image_ref:
            if self.docker_service:
                image_url = self.docker_service.build_container_and_get_image_url(
                    instance.environment.docker_image_ref, push_mode=push_mode
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
        elif instance.environment.vm_image:
            vm_image = VmImage(
                project="deeplearning-platform-release",
                image_family=construct_vm_image_family_from_vm_image(
                    instance.environment.vm_image.framework,
                    instance.environment.vm_image.version,
                    instance.environment.vm_image.os,
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
            instance.boot_disk.disk_type
            if instance.boot_disk
            else None
        )
        boot_disk_size_gb = (
            instance.boot_disk.size_gb if instance.boot_disk else None
        )
        data_disk_type = (
            instance.data_disk.disk_type
            if instance.data_disk
            else None
        )
        data_disk_size_gb = (
            instance.data_disk.size_gb if instance.data_disk else None
        )
        disk_encryption = "CMEK" if self.config.gcp_profile.kms_key else None
        kms_key = (
            self.config.gcp_profile.kms_key if self.config.gcp_profile.kms_key else None
        )

        # service account and instance owners
        service_account = instance.service_account
        instance_owner = self.owner or instance.owner
        instance_owners = [instance_owner] if instance_owner else None

        # labels and tags
        tags = instance.tags
        labels = {
            "wanna_name": instance.name,
            "wanna_resource": self.instance_type,
        }
        if instance_owner:
            labels["wanna_owner"] = email_fixer(instance_owner)
        if instance.labels:
            labels = {**instance.labels, **labels}

        # post startup script
        if deploy and (
            instance.bucket_mounts
            or instance.tensorboard_ref
            or instance.idle_shutdown_timeout
            or self.config.gcp_profile.env_vars
            or instance.env_vars
        ):
            script = self._prepare_startup_script(self.instances[0])
            blob = upload_string_to_gcs(
                script,
                instance.bucket or self.bucket_name,
                f"notebooks/{instance.name}/startup_script.sh",
            )
            post_startup_script = f"gs://{blob.bucket.name}/{blob.name}"
        else:
            post_startup_script = None

        metadata = instance.metadata or {}
        if instance.enable_monitoring:
            enable_monitoring_metadata = {
                "enable-guest-attributes": "TRUE",
                "report-system-health": "TRUE",
                "report-notebook-metrics": "TRUE",
                "install-monitoring-agent": "TRUE",
                "enable-extended-ui": "TRUE",
            }
            metadata = {**metadata, **enable_monitoring_metadata}
        if instance.collaborative:
            collaborative_metadata = {"use-collaborative": "TRUE"}
            metadata = {**metadata, **collaborative_metadata}
        if instance.backup:
            backup_metadata = {"gcs-data-bucket": instance.backup}
            metadata = {**metadata, **backup_metadata}

        instance_proto = Instance(
            vm_image=vm_image,
            container_image=container_image,
            machine_type=instance.machine_type,
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
            no_public_ip=instance.no_public_ip,
            no_proxy_access=instance.no_proxy_access,
        )

        return CreateInstanceRequest(
            parent=f"projects/{instance.project_id}/locations/{instance.zone}",
            instance_id=instance.name,
            instance=instance_proto,
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

    def _client_get_instance(self, instance_id: str) -> Instances:
        return self.notebook_client.get_instance(name=instance_id)

    def _get_jupyterlab_link(self, instance_id: str) -> str:
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
                instance=instance, deploy=False, push_mode=PushMode.manifests
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

    def _return_diff(self) -> tuple[list[NotebookModel], list[NotebookModel]]:
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
