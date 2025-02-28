import itertools
import subprocess
from pathlib import Path

from google.api_core.operation import Operation
from google.cloud import compute_v1
from google.cloud.notebooks_v2 import (
    AcceleratorConfig,
    BootDisk,
    DataDisk,
    GceSetup,
    GPUDriverConfig,
    NetworkInterface,
)
from google.cloud.notebooks_v2.services.notebook_service import NotebookServiceClient
from google.cloud.notebooks_v2.types import (
    ContainerImage,
    CreateInstanceRequest,
    Instance,
    ServiceAccount,
    VmImage,
)

from wanna.core.deployment.models import PushMode
from wanna.core.loggers.wanna_logger import get_logger
from wanna.core.models.wanna_config import WannaConfigModel
from wanna.core.models.workbench import InstanceModel
from wanna.core.services.docker import DockerService
from wanna.core.services.tensorboard import TensorboardService
from wanna.core.services.workbench import BaseWorkbenchService, Instances
from wanna.core.utils import templates
from wanna.core.utils.config_enricher import email_fixer
from wanna.core.utils.gcp import (
    download_script_from_gcs,
    upload_string_to_gcs,
)

logger = get_logger(__name__)


class WorkbenchInstanceService(BaseWorkbenchService[InstanceModel]):
    def __init__(
        self,
        config: WannaConfigModel,
        workdir: Path,
        owner: str | None = None,
        version: str = "dev",
    ):
        super().__init__(
            instance_type="workbench-instance",
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

    def _delete_instance_client(self, instance: InstanceModel) -> Operation:
        return self.notebook_client.delete_instance(
            name=f"projects/{instance.project_id}/locations/"
            f"{instance.zone}/instances/{instance.name}"
        )

    def _create_instance_client(self, request: CreateInstanceRequest) -> Operation:
        return self.notebook_client.create_instance(request)

    def workbench_location(self, instance: InstanceModel) -> str:
        return instance.zone

    def _list_running_instances(self, project_id: str, location: str) -> list[str]:
        """
        list all notebooks with given project_id and location.

        Args:
            project_id: GCP project ID
            location: GCP location (zone)

        Returns:
            instance_names: list of the full names on notebook instances (this includes project_id, and zone)

        """
        instances = self.notebook_client.list_instances(
            parent=f"projects/{project_id}/locations/{location}"
        )
        instance_names = [i.name for i in instances.instances]
        return instance_names

    def _instance_exists(self, instance: InstanceModel) -> bool:
        full_instance_name = (
            f"projects/{instance.project_id}/locations/{instance.zone}/instances/{instance.name}"
        )
        return full_instance_name in self._list_running_instances(
            instance.project_id, instance.zone
        )

    def _create_instance_request(
        self,
        instance: InstanceModel,
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
        subnet = instance.subnet if instance.subnet else self.config.gcp_profile.subnet
        full_subnet_name = self._get_resource_subnet(
            full_network_name,
            subnet,
            instance.region,
        )
        network_interfaces = (
            [
                NetworkInterface(
                    network=full_network_name,
                    subnet=full_subnet_name,
                )
            ]
            if instance.network and instance.subnet
            else None
        )
        # GPU
        if gpu := instance.gpu:
            accelerator_configs = [
                AcceleratorConfig(
                    core_count=gpu.count,
                    type_=gpu.accelerator_type,
                )
            ]
            gpu_driver_config = GPUDriverConfig(
                enable_gpu_driver=gpu.install_gpu_driver,
                custom_gpu_driver_path=gpu.custom_gpu_driver_path,
            )
        else:
            accelerator_configs = None
            gpu_driver_config = None

        # Environment
        if docker_image_ref := instance.environment.docker_image_ref:
            if self.docker_service:
                image_url = self.docker_service.build_container_and_get_image_url(
                    docker_image_ref, push_mode=push_mode
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
        elif vm_i := instance.environment.vm_image:
            vm_image = VmImage(
                project="cloud-notebooks-managed",
                family=f"workbench-instances" if vm_i.version is None else None,
                name=f"workbench-instances-{vm_i.version}" if vm_i.version is not None else None,
            )
            container_image = None
        else:
            raise ValueError(
                "No notebook environment was found. This should not be possible."
                " Something went wrong during model validation"
            )

        # Disks
        disk_encryption = "CMEK" if self.config.gcp_profile.kms_key else None
        kms_key = self.config.gcp_profile.kms_key if self.config.gcp_profile.kms_key else None
        boot_disk = (
            BootDisk(
                disk_size_gb=boot_d.size_gb,
                disk_type=boot_d.disk_type,
                disk_encryption=disk_encryption,
                kms_key=kms_key,
            )
            if (boot_d := instance.boot_disk)
            else None
        )
        data_disks = (
            [
                DataDisk(
                    disk_size_gb=data_d.size_gb,
                    disk_type=data_d.disk_type,
                    disk_encryption=disk_encryption,
                    kms_key=kms_key,
                )
            ]
            if (data_d := instance.data_disk)
            else None
        )

        # service account and instance owners
        service_accounts = [ServiceAccount(email=sa)] if (sa := instance.service_account) else None
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
            or self.config.gcp_profile.env_vars
            or instance.env_vars
        ):
            script = self._prepare_startup_script(instance)

            blob = upload_string_to_gcs(
                script,
                instance.bucket or self.bucket_name,
                f"notebooks/{instance.name}/startup_script.sh",
            )
            post_startup_script = f"gs://{blob.bucket.name}/{blob.name}"
        elif instance.post_startup_script is not None:
            post_startup_script = instance.post_startup_script
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
            # todo: test this
            collaborative_metadata = {"use-collaborative": "TRUE"}
            metadata = {**metadata, **collaborative_metadata}
        # https://cloud.google.com/vertex-ai/docs/workbench/instances/create-dataproc-enabled#terraform
        dataproc_metadata = {"disable-mixer": "false" if instance.enable_dataproc else "true"}
        metadata = {**metadata, **dataproc_metadata}
        # https://cloud.google.com/vertex-ai/docs/workbench/instances/idle-shutdown#terraform
        idle_shutdown_metadata = {
            "idle-timeout-seconds": str(idle_shutdown_timeout * 60)  # we set it in minutes
            if (idle_shutdown_timeout := instance.idle_shutdown_timeout)
            else ""
        }
        metadata = {**metadata, **idle_shutdown_metadata}
        if post_startup_script:
            # https://cloud.google.com/vertex-ai/docs/workbench/instances/manage-metadata
            # https://cloud.google.com/vertex-ai/docs/workbench/instances/create#gcloud
            post_startup_script_metadata = {
                "post-startup-script": post_startup_script,
                "post-startup-script-behavior": instance.post_startup_script_behavior,
            }
            metadata = {**metadata, **post_startup_script_metadata}
        if instance.bucket_mounts and container_image is not None:
            gcsfuse_metadata = {"container-allow-fuse": "true"}
            metadata = {**metadata, **gcsfuse_metadata}
        if instance.environment_auto_upgrade:
            auto_upgrade_metadata = {
                "notebook-upgrade-schedule": instance.environment_auto_upgrade
            }
            metadata = {**metadata, **auto_upgrade_metadata}
        if instance.delete_to_trash:
            delete_to_trash_metadata = {"notebook-enable-delete-to-trash": "true"}
            metadata = {**metadata, **delete_to_trash_metadata}
        report_health_metadata = {
            "report-event-health": "true" if instance.report_health else "false"
        }
        metadata = {**metadata, **report_health_metadata}

        gce_setup = GceSetup(
            machine_type=instance.machine_type,
            accelerator_configs=accelerator_configs,
            service_accounts=service_accounts,
            vm_image=vm_image,
            container_image=container_image,
            boot_disk=boot_disk,
            data_disks=data_disks,
            network_interfaces=network_interfaces,
            disable_public_ip=instance.no_public_ip,
            tags=tags,
            metadata=metadata,
            enable_ip_forwarding=instance.enable_ip_forwarding,
            gpu_driver_config=gpu_driver_config,
        )
        instance_proto = Instance(
            gce_setup=gce_setup,
            instance_owners=instance_owners,
            disable_proxy_access=instance.no_proxy_access,
            labels=labels,
        )

        return CreateInstanceRequest(
            parent=f"projects/{instance.project_id}/locations/{instance.zone}",
            instance_id=instance.name,
            instance=instance_proto,
        )

    def _prepare_startup_script(self, nb_instance: InstanceModel) -> str:
        """
        Prepare the notebook startup script based on the information from notebook.
        This script run at the Compute Engine Instance creation time with a root user.

        Args:
            nb_instance

        Returns:
            startup_script
        """
        env_vars = self.config.gcp_profile.env_vars if self.config.gcp_profile.env_vars else dict()
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

        if nb_instance.post_startup_script is not None:
            # download the script from the bucket
            user_script = download_script_from_gcs(nb_instance.post_startup_script)
            # removing the shebang
            lines = user_script.split("\n")
            if lines and lines[0].startswith("#!"):
                lines = lines[1:]
            user_script = "\n".join(lines)
        else:
            user_script = None

        startup_script = templates.render_template(
            Path("notebook_startup_script.sh.j2"),
            bucket_mounts=nb_instance.bucket_mounts,
            tensorboard_resource_name=tensorboard_resource_name,
            env_vars=env_vars,
            user_script=user_script,
        )
        return startup_script

    def _client_get_instance(self, instance_id: str) -> Instances:
        return self.notebook_client.get_instance(name=instance_id)

    def _get_jupyterlab_link(self, instance_id: str) -> str:
        instance_info = self.notebook_client.get_instance({"name": instance_id})
        return f"https://{instance_info.proxy_uri}"

    def _ssh(
        self, workbench_instance: InstanceModel, run_in_background: bool, local_port: int
    ) -> None:
        """
        SSH connect to the notebook instance if the instance is already started.

        Args:
            workbench_instance: notebook model representing the instance you want to connect to
            run_in_background: whether to run in the background or in interactive mode
            local_port: jupyter lab will be exposed at this port at localhost

        Returns:

        """
        exists = self._instance_exists(workbench_instance)
        if not exists:
            logger.user_info(
                f"Notebook {workbench_instance.name} is not running, create it first and then ssh connect to it."
            )
            return

        bash_command = f"gcloud compute ssh \
             --project {workbench_instance.project_id} \
             --zone {workbench_instance.zone} \
             --tunnel-through-iap \
              {workbench_instance.name} \
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
                raise ValueError(f"Notebook {instance_name} does not exists in configuration")

    def build(self) -> int:
        for instance in self.instances:
            self._create_instance_request(
                instance=instance, deploy=False, push_mode=PushMode.manifests
            )
        logger.user_success("Notebooks validation OK!")
        return 0

    def push(self, instance_name: str):
        instances = self._filter_instances_by_name(instance_name)

        docker_image_refs = {
            instance.environment.docker_image_ref
            for instance in instances
            if instance.environment.docker_image_ref
        }
        if docker_image_refs:
            if self.docker_service:
                for docker_image_ref in docker_image_refs:
                    image_tag = self.docker_service.get_image(docker_image_ref=docker_image_ref)
                    if image_tag[1]:
                        self.docker_service.push_image(image_tag[1])
            else:
                raise Exception("Docker params in wanna-ml config not defined")

    def _return_diff(self) -> tuple[list[InstanceModel], list[InstanceModel]]:
        """
        Figuring out the diff between GCP and wanna.yaml. lists user-managed notebooks to be deleted and created.
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
            InstanceModel.model_validate(
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
