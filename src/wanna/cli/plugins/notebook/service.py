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
from wanna.cli.plugins.notebook.models import NotebookInstance
from wanna.cli.utils import loaders
from wanna.cli.utils import templates
from wanna.cli.utils.gcp.gcp import upload_string_to_gcs
from wanna.cli.utils.gcp.models import WannaProject, GCPSettings
from wanna.cli.utils.spinners import Spinner

GCS_BUCKET_NAME = "wanna-ml"


class NotebookService:
    def __init__(self):
        self.wanna_config_path = None
        self.wanna_project = None
        self.gcp_settings = None
        self.notebooks_instances = []
        self.notebook_client = NotebookServiceClient()

    def create(self, notebook_name: str) -> None:
        """
        Create a Vertex AI workbench notebook with name notebook_name based on wanna-ml config.

        Args:
            notebook_name (str): The name of the only notebook from wanna-ml config that should be created.
                                 Set to "all" to create all notebooks from configuration.
        """
        instances = self._filter_notebooks_by_name(notebook_name)

        for instance in instances:
            self._create_one_instance(instance)

    def delete(self, notebook_name: str) -> None:
        """
        Delete a Vertex AI workbench notebook with name notebook_name based on wanna-ml config if exists on GCP.

        Args:
            notebook_name (str): The name of the only notebook from wanna-ml config that should be deleted.
                                 Set to "all" to create all notebooks from configuration.
        """
        instances = self._filter_notebooks_by_name(notebook_name)

        for instance in instances:
            exists = self._instance_exists(
                project_id=instance.project_id,
                location=instance.zone,
                instance_name=instance.name,
            )
            if exists:
                with Spinner(text=f"Deleting notebook {instance}"):
                    self._delete_one_instance(instance)
            else:
                typer.echo(
                    f"Notebook with name {instance.name} was not found in zone {instance.zone}"
                )

    def _delete_one_instance(self, notebook_instance: NotebookInstance) -> None:
        """
        Delete one notebook instance. This assumes that it has been already verified that notebook exists.

        Args:
            notebook_instance (NotebookInstance): notebook to delete
        """

        deleted = self.notebook_client.delete_instance(
            name=f"projects/{notebook_instance.project_id}/locations/{notebook_instance.zone}/instances/{notebook_instance.name}"
        )
        deleted.result()

    def _create_one_instance(self, notebook_instance: NotebookInstance) -> None:
        """
        Create a notebook instance based on information in NotebookInstance class.
        1. Check if the notebook already exists
        2. Parse the information from NotebookInstance to GCP API friendly format = instance_request
        3. Wait for the compute instance behind the notebook to start
        4. Wait for JupyterLab to start
        5. Get and print the link to JupyterLab

        Args:
            notebook_instance (NotebookInstance): notebook to be created

        """
        exists = self._instance_exists(
            notebook_instance.project_id, notebook_instance.zone, notebook_instance.name
        )
        if exists:
            # TODO: prompt user for request if they want to restart the instance or not
            typer.echo(
                f"Instance {notebook_instance.name} already exists in location {notebook_instance.zone}"
            )
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

    def load_config_from_yaml(self, wanna_config_path: Path) -> None:
        """
        Load the yaml file from wanna_config_path and parses the information to the models.
        This also includes the data validation.

        Args:
            wanna_config_path (Path): path to the wanna-ml yaml file
        """

        with Spinner(text="Reading and validating yaml config"):
            self.wanna_config_path = wanna_config_path
            with open(self.wanna_config_path) as f:
                # Load workflow file
                wanna_dict = loaders.load_yaml(f, Path("."))
            self.wanna_project = WannaProject.parse_obj(wanna_dict.get("wanna_project"))
            self.gcp_settings = GCPSettings.parse_obj(wanna_dict.get("gcp_settings"))

            for nb_instance in wanna_dict.get("notebooks"):
                instance = NotebookInstance.parse_obj(
                    self._enrich_nb_info_with_gcp_settings_dict(nb_instance)
                )
                self.notebooks_instances.append(instance)

    def _enrich_nb_info_with_gcp_settings_dict(self, nb_instance: dict) -> dict:
        """
        The dictionary nb_instance is updated with values from gcp_settings. This allows you to set values such as
        project_id and zone only on the wanna-ml config level but also give you the freedom to set separately for each
        notebook. The values as at the notebook instance take precedence over general wanna-ml settings.

        Args:
            nb_instance (dict): dict with values from wanna-ml config from one notebook

        Returns:
            dict: nb_distance enriched with general gcp_settings if those information was not set on notebook level

        """
        nb_info = self.gcp_settings.dict().copy()
        nb_info.update(nb_instance)
        return nb_info

    def _list_running_instances(self, project_id: str, location: str) -> List[str]:
        """
        List all notebooks with given project_id and location.

        Args:
            project_id (str): GCP project ID
            location (str): GCP location (zone)

        Returns:
            instace_names (List[str]): List of the full names on notebook instances (this includes project_id, and zone)

        """
        instances = self.notebook_client.list_instances(
            parent=f"projects/{project_id}/locations/{location}"
        )
        instance_names = [i.name for i in instances.instances]
        return instance_names

    def _instance_exists(
        self, project_id: str, location: str, instance_name: str
    ) -> bool:
        """
        Check if the instance with given instance_name exists in given GCP project project_id and location.
        Args:
            project_id (str): GCP project ID
            location (str): GCP location (zone)
            instance_name (str): Notebook name to verify

        Returns:
            True if notebook exists, False if not
        """
        full_instance_name = (
            f"projects/{project_id}/locations/{location}/instances/{instance_name}"
        )
        return full_instance_name in self._list_running_instances(project_id, location)

    def _filter_notebooks_by_name(self, notebook_name: str) -> List[NotebookInstance]:
        """
        From self.notebooks_instances filter only the instances with name notebook_name.

        Args:
            notebook_name (str): Name of the notebook to return. Set to "all" to return all instances.

        Returns:
            List[NotebookInstance]

        """
        if notebook_name == "all":
            instances = self.notebooks_instances
            if not instances:
                typer.echo(f"No notebook can be parsed from your wanna-ml yaml config.")
        else:
            instances = [
                nb for nb in self.notebooks_instances if nb.name == notebook_name
            ]
        if not instances:
            typer.echo(
                f"Notebook with name {notebook_name} not found in your wanna-ml yaml config."
            )
        return instances

    def _construct_vm_image_family_from_vm_image(
        self, framework: str, version: str, os: str
    ) -> str:
        """
        Construct name of the Compute Engine VM family with given framework(eg. pytorch), version(eg. 1-9-xla)
        and optional OS (eg. debian-10).

        Args:
            framework (str): VM image framework (pytorch, r, tf2, ...)
            version (str): Version of the framework
            os (str): operation system

        Returns:
            object: Compute Engine VM Family name
        """
        if os:
            return f"{framework}-{version}-notebooks-{os}"
        else:
            return f"{framework}-{version}-notebooks"

    def _create_instance_request(
        self, notebook_instance: NotebookInstance
    ) -> CreateInstanceRequest:
        """
        Transform the information about desired notebook from our NotebookInstance model (based on yaml config)
        to the form suitable for GCP API.

        Args:
            notebook_instance (NotebookInstance)

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
                tag=notebook_instance.environment.container_image.partition(":")[1],
            )
        elif notebook_instance.environment.custom_python_container:
            vm_image = None
            typer.echo(
                "\n Building docker image. This may take a while, stretch your legs or get a \N{hot beverage}"
            )
            container_image_info = self._build_and_push_docker_image(
                image_name=f"{self.wanna_project.name}/{notebook_instance.name}",
                image_version=self.wanna_project.version,
                notebook_instance=notebook_instance,
            )
            container_image = ContainerImage(
                repository=container_image_info.get("repository"),
                tag=container_image_info.get("version"),
            )
        else:
            vm_image = VmImage(
                project=f"deeplearning-platform-release",
                image_family=self._construct_vm_image_family_from_vm_image(
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
        labels.update(self._get_default_labels())

        # post startup script
        if notebook_instance.bucket_mounts:
            script = self._prepare_startup_script(self.notebooks_instances[0])
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

    def _get_default_labels(self) -> dict:
        """
        Get the default labels (GCP labels) that will be used with all notebooks.

        Returns:
            dict
        """
        return {
            "wanna_project": self.wanna_project.name,
            "wanna_project_version": str(self.wanna_project.version),
            "wanna_project_author": self.wanna_project.author.partition("@")[0].replace(
                ".", "_"
            ),
        }

    def _prepare_startup_script(self, nb_instance: NotebookInstance) -> str:
        """
        Prepare the notebook startup script based on the information from notebook.
        This script run at the Compute Engine Instance creation time with a root user.

        Args:
            nb_instance (NotebookInstance)

        Returns:
            startup_script (str)
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
        notebook_instance: NotebookInstance,
        docker_repository="eu.gcr.io/",
        build_args: dict = {},
    ) -> dict:
        """
        Build and puck a docker image.

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
            base_image=notebook_instance.environment.custom_python_container.base_image,
            requirements_txt=notebook_instance.environment.custom_python_container.requirements_file,
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
            instance_id (str): Full notebook instance id
            state (Instance.State): Notebook state (ACTIVE, PENDING,...)

        Returns:
            True if desired state, False otherwise
        """
        try:
            instance_info = self.notebook_client.get_instance({"name": instance_id})
        except exceptions.NotFound:
            raise exceptions.NotFound(
                f"Notebook {instance_id} was not found."
            ) from None
        return instance_info.state == state

    def _get_jupyterlab_link(self, instance_id: str) -> str:
        """
        Get a link to jupyterlab proxy based on given notebook instance id.
        Args:
            instance_id (str): full notebook instance id

        Returns:
            proxy_uri (str): link to jupyterlab
        """
        instance_info = self.notebook_client.get_instance({"name": instance_id})
        return instance_info.proxy_uri
