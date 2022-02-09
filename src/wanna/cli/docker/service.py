import logging
import os
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import typer
from docker import DockerClient
from docker.errors import DockerException
from docker.models.images import Image
from jinja2 import Environment

from wanna.cli.docker.models import DockerBuild, DockerBuildType


class DockerService:
    def __init__(
        self,
        docker_client: DockerClient,
        jinja_env: Environment,
        build_dir: Path,
        working_dir: Path,
        docker_repository: str,
        build_args: Tuple[Tuple[str, str], ...] = tuple(),
        debug: bool = False,
        network_mode: str = "default",
    ) -> None:
        self.docker_client = docker_client
        # TODO: add support for https://pypi.org/project/coloredlogs/#installation
        self.debug_level = logging.DEBUG if debug else logging.INFO

        logging.basicConfig(
            level=self.debug_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(
            "%s.%s" % (self.__class__.__module__, self.__class__.__name__)
        )

        self.build_dir = build_dir
        self.working_dir = working_dir
        self.jinja_env = jinja_env
        self.docker_client = docker_client
        self.docker_repository = docker_repository
        self.build_args = build_args
        self.debug = debug
        self.network_mode = network_mode

    def _extend_tag(self, repository: str, tag: str) -> str:
        return f"{repository}:{tag}"

    def _extend_repository(self, path: str) -> str:
        return f"{self.docker_repository}{path}"

    def _validate_docker_build(self, work_dir: Path, docker_build: DockerBuild) -> None:

        if docker_build.kind == DockerBuildType.Python37:

            if docker_build.conda_env:
                conda_env_path = work_dir / Path(docker_build.conda_env)
                if not conda_env_path.exists():
                    raise ValueError(f"{conda_env_path} does not exist")

            if docker_build.src:
                src_path = work_dir / Path(docker_build.src)
                if not src_path.exists():
                    raise ValueError(f"{src_path} does not exist")

        if docker_build.kind == DockerBuildType.Plain:
            if docker_build.docker_file:
                docker_file_path = work_dir / Path(docker_build.docker_file)
                if not docker_file_path.exists():
                    raise ValueError(f"{docker_file_path} is not a file")

    def _build_image(
        self,
        path: Path,
        docker_file_path: Path,
        stage_name: str,
        version: str,
        build_args: Optional[Dict[str, str]] = None,
    ) -> Tuple[Image, str, str]:

        if build_args is None:
            build_args = {}

        repo = self._extend_repository(str(stage_name))
        tag = self._extend_tag(repo, version)
        image = None
        merged_build_args: Dict[str, str] = {
            **build_args,
            **dict(self.build_args),
        }

        build_generator = self.docker_client.api.build(
            path=str(path),
            dockerfile=str(docker_file_path),
            tag=tag,
            quiet=False,
            rm=True,
            forcerm=True,
            decode=True,
            network_mode=self.network_mode,
            buildargs=merged_build_args,
        )

        for json_output in build_generator:
            if "stream" in json_output:
                if self.debug:
                    typer.echo(json_output["stream"].strip("\n"))
            if "errorDetail" in json_output:
                msg = json_output["errorDetail"]["message"].replace(
                    """\\r\\n""", "\r\n"
                )
                raise DockerException(msg)
        else:
            typer.echo("Docker image build complete.")
            image = self.docker_client.images.get(tag)

        return (image, repo, version)

    def build(
        self,
        version: str,
        work_dir: Path,
        workflow_name: str,
        stage_name: str,
        docker_build: DockerBuild,
    ) -> Tuple[Image, str, str]:
        self._validate_docker_build(work_dir, docker_build)

        docker_build_dir = self.build_dir / workflow_name
        docker_build_dir.mkdir(parents=True, exist_ok=True)

        if hasattr(docker_build, "src") and docker_build.src:
            docker_build_src = self.working_dir / Path(docker_build.src)
            docker_build_dest = docker_build_dir / docker_build.src
            if docker_build_dest.exists():
                shutil.rmtree(docker_build_dest)
            shutil.copytree(docker_build_src, docker_build_dest)

        if hasattr(docker_build, "conda_env") and docker_build.conda_env:
            docker_build_conda_env_src = self.working_dir / Path(docker_build.conda_env)
            docker_build_conda_env_dest = docker_build_dir / docker_build.conda_env
            if docker_build_conda_env_dest.exists():
                os.remove(docker_build_conda_env_dest)

            shutil.copy2(docker_build_conda_env_src, docker_build_conda_env_dest)

        if docker_build.kind == DockerBuildType.GCPBaseImage:
            template = self.jinja_env.get_template("notebook_template.Dockerfile")
            docker_file_path = docker_build_dir / Path(f"{workflow_name}.Dockerfile")

            with open(docker_file_path, "w") as f:
                docker_file = template.render(asdict(docker_build))
                f.write(docker_file)

            shutil.copy2(
                docker_build.requirements_txt,
                docker_build_dir / docker_build.requirements_txt,
            )
            (image, repo, version) = self._build_image(
                path=docker_build_dir,
                docker_file_path=docker_file_path,
                version=version,
                stage_name=str(stage_name),
                build_args=docker_build.build_args,
            )

            return (image, repo, version)

        elif docker_build.kind == DockerBuildType.Plain:
            if hasattr(docker_build, "docker_file") and docker_build.docker_file:
                docker_file_path = self.working_dir / Path(
                    f"{docker_build.docker_file}"
                )

                (image, repo, version) = self._build_image(
                    path=self.working_dir,
                    docker_file_path=docker_file_path,
                    version=version,
                    stage_name=str(stage_name),
                    build_args=docker_build.build_args,
                )
                return (image, repo, version)
            else:
                raise ValueError(
                    f"{DockerBuildType.Plain} must specify a [docker_file]"
                )
        else:
            raise ValueError(f"{docker_build.kind} must specify a [docker_file]")

    def push(
        self,
        images: List[Tuple[Image, str, str, Optional[DockerBuild]]],
        workflow_version: str,
    ) -> None:

        for (_, repo, _, _) in images:
            status = ""
            self.logger.debug("docker push %s:%s", repo, workflow_version)
            for line in self.docker_client.images.push(
                repo, workflow_version, stream=True, decode=True
            ):
                self.logger.debug("%s", line)
                new_status = line.get("status")
                if line.get("errorDetail"):
                    msg = line["errorDetail"]["message"].replace("""\\r\\n""", "\r\n")
                    self.logger.error(
                        "Failed to docker push %s:%s", repo, workflow_version
                    )
                    raise ValueError(msg)
                elif (
                    new_status is not None
                    and new_status != status
                    and not new_status.startswith("The push")
                ):
                    status = new_status
                    self.logger.info(
                        "docker push %s:%s is %s", repo, workflow_version, status
                    )
