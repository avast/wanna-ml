from wanna.cli.utils.gcp.models import WannaProject, GCPSettings
from wanna.cli.plugins.notebook.models import NotebookInstance
from wanna.cli.utils import loaders

from wanna.cli.docker.service import DockerService
from wanna.cli.docker.models import DockerBuild, DockerBuildType

import docker
from jinja2 import Environment, PackageLoader, select_autoescape
from pathlib import Path

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

    def load_notebook_service(self):
        with open(self.wanna_config_path) as f:
            # Load workflow file
            wanna_dict = loaders.load_yaml(f, Path("."))
        self.wanna_project = WannaProject.parse_obj(wanna_dict.get("wanna_project"))
        self.gcp_settings = GCPSettings.parse_obj(wanna_dict.get("gcp_settings"))

        # TODO: better join wanna-project and gcp level information to notebooks
        for nb_instance in wanna_dict.get("notebooks"):
            nb_dict = {}
            nb_dict.update(self.gcp_settings.dict())
            nb_dict.update(nb_instance)
            instance = NotebookInstance.parse_obj(nb_dict)
            self.notebooks_instances.append(instance)

        instance_request = self._create_instance_request(
            notebook_instance=self.notebooks_instances[0]
        )
        instance = self.notebook_client.create_instance(instance_request)
        instance.result()

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
        print("Creating instance request")
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
            post_startup_script=None # TODO: create startup script to mount GCS bucket
        )

        return CreateInstanceRequest(
            parent=f"projects/{notebook_instance.project_id}/locations/{notebook_instance.zone}",
            instance_id=notebook_instance.name,
            instance=instance,
        )

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
