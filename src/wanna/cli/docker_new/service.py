from pathlib import Path
from typing import Union, List
import shutil

from python_on_whales import docker, Image
from wanna.cli.models.docker_container import ContainerImageModel, ContainerBuildType
from wanna.cli.utils.templates import render_template


class DockerClientException(Exception):
    pass


class DockerService:
    def __init__(self, work_dir: Path):
        assert self._is_docker_client_active(), DockerClientException(
            "You need running docker client on your machine"
        )
        self.work_dir = work_dir
        self.build_dir = self.work_dir / Path("build")

    @staticmethod
    def _is_docker_client_active() -> bool:
        return docker.info().id is not None

    def build_image(
        self, image_model: ContainerImageModel, tags: Union[str, List[str]], **kwargs
    ) -> Image:
        if image_model.type == ContainerBuildType.notebook_ready_image:
            self._jinja_render_dockerfile(image_model)
        ...

    def push_image(self, image: Image) -> None:
        ...

    def tag_image(self, image: Image, new_tag: str) -> None:
        ...

    def remove_image(self, image: Image, force=False, prune=True) -> None:
        ...

    def _jinja_render_dockerfile(self, image_model: ContainerImageModel):
        if image_model.type == ContainerBuildType.notebook_ready_image:
            source_path = Path("src/wanna/cli/templates/notebook_template.Dockerfile")
            shutil.copy2(
                self.work_dir / image_model.requirements_txt,
                self.build_dir / image_model.requirements_txt,
            )
        else:
            raise Exception(
                f"Source Dockerfile template not found for container build type {image_model.type.name}"
            )

        rendered = render_template(
            source_path=source_path,
            base_image=image_model.base_image,
            requirements_txt=image_model.requirements_txt,
        )
        docker_file_path = self.build_dir / Path(f"{image_model.name}.Dockerfile")
        with open(docker_file_path, "w") as f:
            f.write(rendered)
