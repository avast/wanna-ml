import logging

# import os
# import shutil
# from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from python_on_whales import Image, docker

from wanna.cli.docker.models import DockerBuild


class DockerService:
    def __init__(
        self,
        build_dir: Path,
        working_dir: Path,
        docker_repository: str,
        build_args: Tuple[Tuple[str, str], ...] = tuple(),
        debug: bool = False,
        network_mode: str = "default",
    ) -> None:

        # TODO: add support for https://pypi.org/project/coloredlogs/#installation
        self.debug_level = logging.DEBUG if debug else logging.INFO

        logging.basicConfig(
            level=self.debug_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))

        self.build_dir = build_dir
        self.working_dir = working_dir
        self.docker_repository = docker_repository
        self.build_args = build_args
        self.debug = debug
        self.network_mode = network_mode

    def _extend_tag(self, repository: str, tag: str) -> str:
        return f"{repository}:{tag}"

    def _extend_repository(self, path: str) -> str:
        return f"{self.docker_repository}/{path}"

    def build(
        self,
        docker_build: DockerBuild,
        image_name: str,
        project_dir: Path,
        version: str,
        build_args: Optional[Dict[str, str]] = None,
        platforms: Optional[List[str]] = None,
        ssh: Optional[str] = None,
    ) -> Tuple[Image, str, str, str]:

        if build_args is None:
            build_args = {}

        repo = self._extend_repository(image_name)
        tag = self._extend_tag(repo, version)
        merged_build_args: Dict[str, str] = {
            **build_args,
            **dict(self.build_args),
        }

        docker.buildx.build(
            context_path=project_dir / docker_build.context,
            file=project_dir / docker_build.dockerfile,
            tags=[tag],
            network=self.network_mode,
            build_args=merged_build_args,
            # load=True, # Return image
            platforms=platforms,
            progress="auto",  # auto, plain, tty, or False
            ssh=ssh,
            # output https://gabrieldemarmiesse.github.io/python-on-whales/sub-commands/buildx/
        )

        image = docker.image.inspect(tag)

        return (image, repo, tag, version)

    def push(
        self,
        images: List[Tuple[Image, str, str, Optional[DockerBuild]]],
        workflow_version: str,
    ) -> None:

        for (image, repo, _, _) in images:
            self.logger.debug("docker push %s:%s:%s", image, repo, workflow_version)
            # docker.push(repo, quiet=True)
