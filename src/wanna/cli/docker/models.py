import itertools
import re
import shlex
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Dict, List, Optional, Union

from pathvalidate._filepath import validate_filepath
from wanna.cli.utils import text


@unique
class DockerBuildType(Enum):
    """
    An Enum that represents what type of docker build should be executed

    Attributes
    ----------
    Python37 : str
        represents the default Python37 MLOps image
    Plain : str
        represents a Dockerfile based build
    Provided : str
        represents an already built image
        provided by the user from outside a worflow repo
    GCPBaseImage : str
        represents an image that will be base on Deep Learning image provided by google
        https://cloud.google.com/deep-learning-containers/docs/overview
    """

    Python37 = "python37"
    Plain = "plain"
    Provided = "provided"
    GCPBaseImage = "gcp_base_image"


@dataclass
class DockerRef:
    """
    A reference to a docker build to be used in a
    workflow stage

    Attributes
    ----------
    image_ref : str
        the id of the docker build
    command : str
        docker command to be executes
    environment : str
        extra ENV k=v values for docker run
    volumes : str
        extra volumes k:v values for docker run

    Methods
    -------
    get_docker_run(repo: str,
                   tag: str,
                   environment: List[str],
                   volumes: List[str],
                   env_files: List[str])
        extend class and generate docker run command
    """

    image_ref: str
    command: List[Union[str, int]]
    enable_gpu: bool = field(default=False)
    environment: List[str] = field(default_factory=list)
    volumes: List[str] = field(default_factory=list)
    env_files: List[str] = field(default_factory=list)

    _volumes_pattern = re.compile(
        "(\\/[\\/a-zA-Z0-9._-]+):(\\/[\\/\\a-zA-Z0-9._-]+)(:[ro]+)?"
    )

    _envs_pattern = re.compile("^(.*)=(.*)$")

    _path_pattern = re.compile("(\\/[\\/a-zA-Z0-9._-]+)")

    def get_docker_run(
        self,
        name: str,
        repo: str,
        tag: str,
        environment: List[str],
        volumes: List[str],
        env_files: List[str],
    ) -> str:

        cmd = self._get_docker_run_cmd(name, repo, tag, environment, volumes, env_files)
        escaped_cmd = self._preprocess_params(cmd)
        final_cmd = " ".join(x for x in list(filter(None, escaped_cmd)))
        return final_cmd

    def _preprocess_params(self, cmd: List[str]) -> List[str]:
        quoted_cmd = []
        for param in cmd:
            if param.startswith(("--", "-")):
                elements = param.split(" ", 1)
                for el in elements:
                    quoted_cmd.append(shlex.quote(el))
            else:
                quoted_cmd.append(shlex.quote(param))
        return quoted_cmd

    def _format(self, docker_flag: str, args: List[str]) -> str:
        return "".join([f"{docker_flag} {arg} \\\n              " for arg in args])

    def _get_docker_run_cmd(
        self,
        name: str,
        repo: str,
        tag: str,
        environment: List[str],
        volumes: List[str],
        env_files: List[str],
    ) -> List[str]:

        # Collect docker image
        image_tag = tag
        if not tag.startswith(repo):
            image_tag = f"{repo}:{tag}"

        # Cascade & collect docker volumes
        all_volumes = set(itertools.chain(self.volumes, volumes))
        clean_volumes = []
        for volume in sorted(all_volumes):
            if self._volumes_pattern.match(volume):
                clean_volumes.append("-v")
                clean_volumes.append(volume.strip())
            else:
                raise ValueError(
                    f"Volume: {volume} does not match regex {self._volumes_pattern}"
                )

        # Cascade & collect docker ENVs
        all_envs = set(itertools.chain(self.environment, environment))
        clean_envs = []

        for env in sorted(all_envs):
            if self._envs_pattern.match(env):
                clean_envs.append("-e")
                clean_envs.append(env.strip())
            else:
                raise ValueError(
                    f"Env: {env} does not match regex {self._envs_pattern}"
                )

        # Cascade & collect docker ENV files paths
        all_env_files = set(itertools.chain(self.env_files, env_files))
        clean_env_files = []

        for env_file in sorted(all_env_files):
            validate_filepath(env_file, platform="auto")
            clean_env_files.append("--env-file")
            clean_env_files.append(env_file.strip())

        gpu_flag: List[str] = ["--gpus", "all"] if self.enable_gpu else []
        shared_memory_flag: List[str] = ["--ipc", "host"] if self.enable_gpu else []
        cmd: List[str] = (
            [
                "docker",
                "run",
                "--network",
                "host",
                "--rm",
                "--name",
                text.to_snake_case(name),
            ]
            + gpu_flag
            + shared_memory_flag
            + clean_volumes
            + clean_env_files
            + clean_envs
            + [image_tag]
            + list(map(lambda c: str(c), self.command))
        )

        return cmd


@dataclass
class DockerBuild:
    """
    Docker build to be used in a workflow stage

    Attributes
    ----------
    kind : DockerBuildType
        kind to give us the freedom to select what kind of images we support
    conda_env : str
        relative path to a conda file, if present it will be used to update env in docker
    requirements_txt : str
        relative path to a requirements.txt file, if present it will be used to update env
    src : str
        source code directory to be copied to /workflow dir in the docker image
    docker_file : str
        user provided Dockerfile just build it
    push : str
        whether we should also push the image after build.
        useful for when building images just for tests purposes
    """

    kind: DockerBuildType = field(metadata={"by_value": True})
    conda_env: Optional[str] = field(default=None)
    requirements_txt: Optional[str] = field(default=None)
    src: Optional[str] = field(default=None)
    docker_file: Optional[str] = field(default=None)
    push: Optional[bool] = field(default=True)
    build_args: Dict[str, str] = field(default_factory=dict)
    base_image: Optional[str] = field(default=None)
