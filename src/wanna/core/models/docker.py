import sys
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

from pydantic import BaseModel, Extra, Field


class DockerBuildConfigModel(BaseModel, extra=Extra.forbid):
    # Docu for more info: https://gabrieldemarmiesse.github.io/python-on-whales/sub-commands/buildx/#build
    build_args: Dict[str, str] = {}
    add_hosts: Dict[str, str] = {}
    labels: Dict[str, str] = {}
    network: Optional[str]
    platforms: Optional[List[str]]
    secrets: Union[str, List[str]] = []
    ssh: Optional[str]
    target: Optional[str]


class ImageBuildType(str, Enum):
    local_build_image = "local_build_image"
    provided_image = "provided_image"
    notebook_ready_image = "notebook_ready_image"


class BaseDockerImageModel(BaseModel, extra=Extra.forbid, validate_assignment=True):
    name: str = Field(min_length=3, max_length=128)


class LocalBuildImageModel(BaseDockerImageModel):
    build_type: Literal[ImageBuildType.local_build_image]
    build_args: Optional[Dict[str, str]]
    context_dir: Path
    dockerfile: Path


class ProvidedImageModel(BaseDockerImageModel):
    build_type: Literal[ImageBuildType.provided_image]
    image_url: str


class NotebookReadyImageModel(BaseDockerImageModel):
    build_type: Literal[ImageBuildType.notebook_ready_image]
    build_args: Optional[Dict[str, str]]
    base_image: str = "gcr.io/deeplearning-platform-release/base-cpu"
    requirements_txt: Path


DockerImageModel = Union[LocalBuildImageModel, ProvidedImageModel, NotebookReadyImageModel]


class DockerModel(BaseModel, extra=Extra.forbid, validate_assignment=True):
    images: List[DockerImageModel] = []
    repository: str
    registry: Optional[str] = None
    cloud_build: bool = False


class DockerBuildResult(BaseModel, extra=Extra.forbid):
    name: str
    tags: List[str]
    build_type: ImageBuildType
