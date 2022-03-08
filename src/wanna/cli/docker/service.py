import os
import shutil
from pathlib import Path
from typing import List

from python_on_whales import docker, Image
from wanna.cli.models.docker import DockerImageModel, ImageBuildType
from wanna.cli.utils.templates import render_template


class DockerClientException(Exception):
    pass


class DockerService:
    def __init__(self):
        assert self._is_docker_client_active(), DockerClientException(
            "You need running docker client on your machine"
        )

    @staticmethod
    def _is_docker_client_active() -> bool:
        """
        Method to find out if you have a running docker client on your machine.

        Returns:
            True if docker client found, False otherwise
        """
        return docker.info().id is not None

    def build_image(
        self,
        image_model: DockerImageModel,
        tags: List[str],
        work_dir: Path = Path("."),
        **kwargs,
    ) -> Image:
        """
        Method to build docker image from DockerImageModel.
        Args:
            image_model: DockerImageModel with complete information about the docker image
            tags: tags for the image
            work_dir: working directory
            **kwargs: optional arguments to the python_on_whales image build

        Returns:

        """
        build_dir = work_dir / Path("build") / image_model.name
        os.makedirs(build_dir, exist_ok=True)
        if image_model.build_type == ImageBuildType.notebook_ready_image:
            template_path = Path("src/wanna/cli/templates/notebook_template.Dockerfile")
            shutil.copy2(
                work_dir / image_model.requirements_txt,
                build_dir / "requirements.txt",
            )
            file_path = self._jinja_render_dockerfile(
                image_model, template_path, build_dir=build_dir
            )
            context_dir = build_dir
        elif image_model.build_type == ImageBuildType.local_build_image:
            file_path = image_model.dockerfile
            context_dir = image_model.context_dir
        else:
            raise Exception("Invalid image model type.")
        image = docker.build(context_dir, file=file_path, tags=tags, **kwargs)
        return image

    @staticmethod
    def push_image(image: Image) -> None:
        """
        Push a docker image to the registry (image must have tags)
        Args:
            image: image to push
        """
        docker.image.push(image.repo_tags)

    @staticmethod
    def remove_image(image: Image, force=False, prune=True) -> None:
        """
        Remove docker image, useful if you dont want to clutter your machine.
        """
        docker.image.remove(image, force=force, prune=prune)

    @staticmethod
    def construct_image_tag(
        registry: str, project: str, image_name: str, version: str = "latest"
    ):
        """
        Construct full image tag.
        Args:
            registry:
            project:
            image_name:
            version:

        Returns:
            full image tag
        """
        return f"{registry}/{project}/{image_name}:{version}"

    @staticmethod
    def _jinja_render_dockerfile(
        image_model: DockerImageModel,
        template_path: Path,
        build_dir: Path,
    ) -> Path:
        """
        Based on image_model.type, we render dockerfile for this image type.
        Args:
            image_model: docker image model
            template_path: path to the dockerfile jinja template
            build_dir: build directory (where to save rendered dockerfile)

        Returns:
            path to the rendered dockerfile
        """
        if image_model.build_type == ImageBuildType.notebook_ready_image:
            rendered = render_template(
                source_path=template_path,
                base_image=image_model.base_image,
                requirements_txt=image_model.requirements_txt,
            )
        else:
            raise Exception("Invalid docker image type.")
        docker_file_path = build_dir / Path(f"{image_model.name}.Dockerfile")
        with open(docker_file_path, "w") as file:
            file.write(rendered)
        return docker_file_path
