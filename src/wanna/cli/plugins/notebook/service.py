from wanna.cli.utils.gcp.models import WannaProject, GCPSettings
from wanna.cli.plugins.notebook.models import NotebookInstance
from wanna.cli.utils import loaders
from wanna.cli.utils import templates
from wanna.cli.utils.gcp.gcp import upload_string_to_gcs
from wanna.cli.docker.service import DockerService
from wanna.cli.docker.models import DockerBuild, DockerBuildType

import docker
from jinja2 import Environment, PackageLoader, select_autoescape
from pathlib import Path
from waiting import wait

import typer

from google.api_core import exceptions
from google.cloud.notebooks_v1.services.notebook_service import NotebookServiceClient
from google.cloud.notebooks_v1.types import (
    ListInstancesRequest,
    Instance,
    CreateInstanceRequest,
    VmImage,
    ContainerImage,
)


class NotebookService:
    def __init__(
        self,
        wanna_config_path: Path,
    ):
        self.wanna_config_path = wanna_config_path
        self.wanna_project = None
        self.gcp_settings = None
        self.notebooks_instances = []
        self.notebook_client = NotebookServiceClient()

    def _enrich_nb_info_with_gcp_settings_dict(self, nb_instance: dict) -> dict:
        nb_info = self.gcp_settings.dict().copy()
        nb_info.update(nb_instance)
        return nb_info

    def create(self):
        self.create_one_instance(self.notebooks_instances[0])

    def create_one_instance(self, notebook_instance: NotebookInstance):
        exists = self._instance_exists(
            notebook_instance.project_id, notebook_instance.zone, notebook_instance.name
        )
        if exists:
            # TODO: prompt user for request if they want to restart the instance or not
            typer.echo(
                f"Instance {notebook_instance.name} already exists in location {notebook_instance.zone}"
            )
            return
        typer.echo("Creating underlying compute engine instance")
        instance_request = self._create_instance_request(
            notebook_instance=notebook_instance
        )
        instance = self.notebook_client.create_instance(instance_request)
        instance_full_name = (
            instance.result().name
        )  # .result() waits for compute engine behind the notebook to start
        typer.echo("Instance created. Waiting for jupyterlab to start")
        wait(
            lambda: self._validate_jupyterlab_state(
                instance_full_name, Instance.State.ACTIVE
            ),
            timeout_seconds=450,
            sleep_seconds=20,
            waiting_for="Starting JupyterLab in your instance",
        )
        jupyterlab_link = self._get_jupyterlab_link(instance_full_name)
        typer.echo(f"JupyterLab started at {jupyterlab_link}")

    def load_notebook_service(self):
        typer.echo("validating yaml file")
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

    def _list_running_instances(self, gcp_project: str, location: str) -> list:
        instances = self.notebook_client.list_instances(
            ListInstancesRequest(parent=f"projects/{gcp_project}/locations/{location}")
        )
        instance_names = [i.name for i in instances.instances]
        return instance_names

    def _instance_exists(
        self, gcp_project: str, location: str, instance_name: str
    ) -> bool:
        full_instance_name = (
            f"projects/{gcp_project}/locations/{location}/instances/{instance_name}"
        )
        return full_instance_name in self._list_running_instances(gcp_project, location)

    def _construct_vm_image_family_from_vm_image(
        self, framework: str, version: str, os: str
    ) -> VmImage:
        if os:
            return f"{framework}-{version}-notebooks-{os}"
        else:
            return f"{framework}-{version}-notebooks"

    def _create_instance_request(
        self, notebook_instance: NotebookInstance
    ) -> CreateInstanceRequest:
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
            post_startup_script = self._upload_startup_script(script)
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
        return {
            "wanna_project": self.wanna_project.name,
            "wanna_project_version": str(self.wanna_project.version),
            "wanna_project_author": self.wanna_project.author.partition("@")[0].replace(
                ".", "_"
            ),
        }

    def _prepare_startup_script(self, nb_instance: NotebookInstance) -> str:
        bucket_mounts = nb_instance.bucket_mounts
        startup_script = templates.render_template(
            "src/wanna/cli/templates/notebook_startup_script.sh.j2",
            bucket_mounts=bucket_mounts,
        )
        return startup_script

    def _upload_startup_script(self, script: str) -> str:
        blob = upload_string_to_gcs(
            script, "us-burger-gcp-poc-mooncloud", "startup_script.sh"
        )
        return f"gs://{blob.bucket.name}/{blob.name}"

    def _build_and_push_docker_image(
        self,
        image_name: str,
        image_version: str,
        notebook_instance: NotebookInstance,
        docker_repository="eu.gcr.io/",
        build_args: dict = {},
    ) -> dict:
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
        try:
            instance_info = self.notebook_client.get_instance({"name": instance_id})
        except exceptions.NotFound:
            raise exceptions.NotFound(
                f"Notebook {instance_id} was not found."
            ) from None
        return instance_info.state == state

    def _get_jupyterlab_link(self, instance_id: str) -> str:
        instance_info = self.notebook_client.get_instance({"name": instance_id})
        return instance_info.proxy_uri
