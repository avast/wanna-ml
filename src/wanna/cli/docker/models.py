from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Dict, List, Optional

from serde import deserialize, serialize


@serialize
@deserialize
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
    """

    Plain = "plain"
    Provided = "provided"


@serialize
@deserialize
@dataclass
class DockerBuild:
    """
    Docker build to be used in a workflow stage

    Attributes
    ----------
    src : str
        source code directory to be copied to /workflow dir in the docker image
    docker_file : str
        user provided Dockerfile just build it
    push : str
        whether we should also push the image after build.
        useful for when building images just for tests purposes
    """

    context: str
    dockerfile: str
    add_hosts: Dict[str, str] = field(default_factory=dict)
    build_args: Dict[str, str] = field(default_factory=dict)
    cache: bool = field(default=True)
    labels: Dict[str, str] = field(default_factory=dict)
    network: Optional[str] = field(default="default")
    platforms: Optional[List[str]] = field(default_factory=["linux/amd64"])
    target: Optional[str] = field(default=None)
    ssh: Optional[str] = field(default="default")
