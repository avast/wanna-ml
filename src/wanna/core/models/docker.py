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
    """
    - `build_type` - [str] "local_build_image"
    - `name` - [str] This will later be used in `docker_image_ref` in other resources
    - `build_args` [Dict[str, str]] - (optional) docker build args
    - `context_dir` [Path] - Path to the docker build context directory
    - `dockerfile` [Path] - Path to the Dockerfile
    """

    build_type: Literal[ImageBuildType.local_build_image]
    build_args: Optional[Dict[str, str]]
    context_dir: Path
    dockerfile: Path


class ProvidedImageModel(BaseDockerImageModel):
    """
    - `build_type` - [str] "provided_image"
    - `name` - [str] This will later be used in `docker_image_ref` in other resources
    - `image_url` - [str] URL link to the image
    """

    build_type: Literal[ImageBuildType.provided_image]
    image_url: str


class NotebookReadyImageModel(BaseDockerImageModel):
    """
    - `build_type` - [str] "notebook_ready_image"
    - `name` - [str] This will later be used in `docker_image_ref` in other resources
    - `build_args` [Dict[str, str]] - (optional) docker build args
    - `base_image` [str] - (optional) base notebook docker image, you can check
    available images https://cloud.google.com/deep-learning-vm/docs/images
      when not set, it defaults to standard base CPU notebook.
    - `requirements_txt` [Path] - Path to the `requirements.txt` file containing python packages that will be installed
    """

    build_type: Literal[ImageBuildType.notebook_ready_image]
    build_args: Optional[Dict[str, str]]
    base_image: str = "gcr.io/deeplearning-platform-release/base-cpu"
    requirements_txt: Path


DockerImageModel = Union[
    LocalBuildImageModel, ProvidedImageModel, NotebookReadyImageModel
]


class DockerModel(BaseModel, extra=Extra.forbid, validate_assignment=True):
    """
    - `images`- [List[Union[LocalBuildImageModel, ProvidedImageModel, NotebookReadyImageModel]]] Docker images
    that will be used in wanna-ml resources
    - `repository` - [str] (optional) GCP Artifact Registry repository for pushing images
    - `registry` - [str] (optional) GCP Artifact Registry, when not set it defaults
    to `{gcp_profile.region}-docker.pkg.dev`
    - `cloud_build_timeout` - [int] `12000` how many seconds before cloud build timeout
    - `cloud_build` - [str] (optional) `false` (default) to build locally, `true` to use GCP Cloud Build
    - `cloud_build_workerpool` - [str] (optional) Name of the GCP Cloud Build workerpool if you want to use one
    - `cloud_build_workerpool_location` - [str] (optional) Location of the GCP Cloud Build workerpool. Must be specified
    if cloud_build_workerpool is set.
    - `cloud_build_kaniko_version` - [str] (optional) which https://github.com/GoogleContainerTools/kaniko/ version to use
    - `cloud_build_kaniko_flags` - [str] (optional) which https://github.com/GoogleContainerTools/kaniko/ flags to use
    """

    images: List[DockerImageModel] = []
    repository: Optional[str]
    registry: Optional[str]
    cloud_build_timeout: int = 12000
    cloud_build: bool = False
    cloud_build_workerpool: Optional[str]
    cloud_build_workerpool_location: Optional[str]
    cloud_build_kaniko_version: Optional[str] = "latest"
    cloud_build_kaniko_flags: List[str] = [
        "--cache=true",
        "--compressed-caching=false",
        "--cache-copy-layers=true",
    ]


class DockerBuildResult(BaseModel, extra=Extra.forbid):
    name: str
    tags: List[str]
    build_type: ImageBuildType
