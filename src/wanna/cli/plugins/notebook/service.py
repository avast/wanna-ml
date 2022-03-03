from pathlib import Path
from typing import List

import docker
import typer
from google.api_core import exceptions
from google.cloud.notebooks_v1.services.notebook_service import NotebookServiceClient
from google.cloud.notebooks_v1.types import (
    Instance,
    CreateInstanceRequest,
    VmImage,
    ContainerImage,
)
from jinja2 import Environment, PackageLoader, select_autoescape
from waiting import wait
from wanna.cli.docker.models import DockerBuild, DockerBuildType
from wanna.cli.docker.service import DockerService
from wanna.cli.models.notebook import NotebookModel
from wanna.cli.models.wanna_config import WannaConfigModel
from wanna.cli.plugins.base.service import BaseService
from wanna.cli.utils import templates
from wanna.cli.utils.gcp.gcp import (
    upload_string_to_gcs,
    construct_vm_image_family_from_vm_image,
)
from wanna.cli.utils.spinners import Spinner

GCS_BUCKET_NAME = "wanna-ml"  # TODO: read from env variable or settings


class NotebookService(BaseService):
    def __init__(self):
        super().__init__(
            instance_type="notebook",
            instance_model=NotebookModel,
        )
        self.notebook_client = NotebookServiceClient()

    def load_config(self, config: WannaConfigModel):
        self.instances = config.notebooks
        self.wanna_project = config.wanna_project

    def _delete_one_instance(self, notebook_instance: NotebookModel) -> None:
        """
        Delete one notebook instance. This assumes that it has been already verified that notebook exists.

        Args:
            notebook_instance: notebook to delete
        """

        with Spinner(text=f"Deleting {self.instance_type} {notebook_instance.name}"):
            deleted = self.notebook_client.delete_instance(
                name=f"projects/{notebook_instance.project_id}/locations/{notebook_instance.zone}/instances/{notebook_instance.name}"
            )
            deleted.result()

    def _create_one_instance(self, notebook_instance: NotebookModel) -> None:
        """
        Create a notebook instance based on information in NotebookModel class.
        1. Check if the notebook already exists
        2. Parse the information from NotebookModel to GCP API friendly format = instance_request
        3. Wait for the compute instance behind the notebook to start
        4. Wait for JupyterLab to start
        5. Get and print the link to JupyterLab

        Args:
            notebook_instance: notebook to be created

        """
        exists = self._instance_exists(notebook_instance)
        if exists:
            typer.echo(
                f"Instance {notebook_instance.name} already exists in location {notebook_instance.zone}"
            )
            should_recreate = typer.confirm(
                "Are you sure you want to delete it and start a new?"
            )
            if should_recreate:
                self._delete_one_instance(notebook_instance)
            else:
                return
        with Spinner(
            text=f"Creating underlying compute engine instance for {notebook_instance.name}"
        ):
            instance_request = self._create_instance_request(
                notebook_instance=notebook_instance
            )
            instance = self.notebook_client.create_instance(instance_request)
            instance_full_name = (
                instance.result().name
            )  # .result() waits for compute engine behind the notebook to start
        with Spinner(text="Starting JupyterLab"):
            wait(
                lambda: self._validate_jupyterlab_state(
                    instance_full_name, Instance.State.ACTIVE
                ),
                timeout_seconds=450,
                sleep_seconds=20,
                waiting_for="Starting JupyterLab in your instance",
            )
            jupyterlab_link = self._get_jupyterlab_link(instance_full_name)
        typer.echo(f"\N{party popper} JupyterLab started at {jupyterlab_link}")

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
        self, notebook_instance: NotebookModel
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
        if notebook_instance.network:
            network_name = notebook_instance.network.network_id
            subnet_name = notebook_instance.network.subnet
            full_network_name = f"projects/{notebook_instance.project_id}/global/networks/{network_name}"
            if subnet_name:
                full_subnet_name = f"projects/{notebook_instance.project_id}/region/{notebook_instance.zone}/subnetworks/{subnet_name}"
            else:
                full_subnet_name = None
        else:
            full_network_name, full_subnet_name = None, None
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
        if notebook_instance.environment.container_image:
            vm_image = None
            container_image = ContainerImage(
                repository=notebook_instance.environment.container_image.partition(":")[
                    0
                ],
                tag=notebook_instance.environment.container_image.partition(":")[-1],
            )
        elif notebook_instance.environment.custom_container:
            vm_image = None
            typer.echo(
                "\n Building docker image. This may take a while, stretch your legs or get a \N{hot beverage}"
            )
            container_image_info = self._build_and_push_docker_image(
                image_name=f"{self.wanna_project.name}/{notebook_instance.name}",
                image_version=self.wanna_project.version,
                notebook_instance=notebook_instance,
                docker_repository="eu.gcr.io/",
            )
            container_image = ContainerImage(
                repository=container_image_info.get("repository"),
                tag=container_image_info.get("version"),
            )
        else:
            vm_image = VmImage(
                project=f"deeplearning-platform-release",
                image_family=construct_vm_image_family_from_vm_image(
                    notebook_instance.environment.vm_image.framework,
                    notebook_instance.environment.vm_image.version,
                    notebook_instance.environment.vm_image.os,
                ),
            )
            container_image = None
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

        # service account and instance owners
        service_account = notebook_instance.service_account
        instance_owners = (
            [notebook_instance.instance_owner]
            if notebook_instance.instance_owner
            else None
        )

        # labels and tags
        tags = notebook_instance.tags
        labels = notebook_instance.labels if notebook_instance.labels else {}

        # post startup script
        if notebook_instance.bucket_mounts:
            script = self._prepare_startup_script(self.instances[0])
            blob = upload_string_to_gcs(
                script,
                GCS_BUCKET_NAME,
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
        startup_script = templates.render_template(
            "src/wanna/cli/templates/notebook_startup_script.sh.j2",
            bucket_mounts=bucket_mounts,
        )
        return startup_script

    def _build_and_push_docker_image(
        self,
        image_name: str,
        image_version: str,
        notebook_instance: NotebookModel,
        docker_repository: str,
        build_args: dict = {},
    ) -> dict:
        """
        Build and push a docker image.

        Args:
            image_name:
            image_version:
            notebook_instance:
            docker_repository:
            build_args:

        Returns:

        """
        docker_client = docker.from_env()
        jinja_env = Environment(
            loader=PackageLoader("wanna", "cli/templates"),
            autoescape=select_autoescape(["html", "xml"]),
        )
        workdir = Path(Path(self.wanna_config_path).parent.absolute())
        build_dir = workdir / Path("build")
        build_args = tuple()  # TODO: parse build args from wanna.yaml
        docker_service = DockerService(
            docker_client,
            jinja_env,
            build_dir,
            workdir,
            docker_repository,
            build_args,
        )
        build = DockerBuild(
            kind=DockerBuildType.GCPBaseImage,
            base_image=notebook_instance.environment.custom_container.base_image,
            requirements_txt=notebook_instance.environment.custom_container.requirements_file,
        )
        full_image_name = (
            f"{notebook_instance.project_id}/vertex-ai-notebooks/{image_name}"
        )
        (image, repository, tag) = docker_service.build(
            image_version,
            workdir,
            notebook_instance.name,
            full_image_name,
            build,
        )
        docker_service.push([(image, repository, "", build)], image_version)
        return {"repository": repository, "version": str(image_version)}

    def _validate_jupyterlab_state(
        self, instance_id: str, state: Instance.State
    ) -> bool:
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
        return instance_info.proxy_uri
