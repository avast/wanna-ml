from enum import Enum
from pathlib import Path
from typing import Literal, Union

from pydantic import BaseModel, ConfigDict, Field


class DockerBuildConfigModel(BaseModel):
    # Docu for more info: https://gabrieldemarmiesse.github.io/python-on-whales/sub-commands/buildx/#build
    build_args: dict[str, str] = Field(default_factory=dict)
    add_hosts: dict[str, str] = Field(default_factory=dict)
    labels: dict[str, str] = Field(default_factory=dict)
    network: str | None = None
    platforms: list[str] | None = None
    secrets: str | list[str] = Field(default_factory=lambda: [])
    ssh: str | None = None
    target: str | None = None

    model_config = ConfigDict(extra="forbid")


class ImageBuildType(str, Enum):
    local_build_image = "local_build_image"
    provided_image = "provided_image"
    notebook_ready_image = "notebook_ready_image"


class BaseDockerImageModel(BaseModel):
    name: str = Field(..., min_length=3, max_length=128)

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class LocalBuildImageModel(BaseDockerImageModel):
    """
    - `build_type` - [str] "local_build_image"
    - `name` - [str] This will later be used in `docker_image_ref` in other resources
    - `build_args` [dict[str, str]] - (optional) docker build args
    - `context_dir` [Path] - Path to the docker build context directory
    - `dockerfile` [Path] - Path to the Dockerfile
    """

    build_type: Literal[ImageBuildType.local_build_image]
    build_args: dict[str, str] | None = None
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
    - `build_args` [dict[str, str]] - (optional) docker build args
    - `base_image` [str] - (optional) base notebook docker image, you can check
    available images https://cloud.google.com/deep-learning-vm/docs/images
      when not set, it defaults to standard base CPU notebook.
    - `requirements_txt` [Path] - Path to the `requirements.txt` file containing python packages that will be installed
    """

    build_type: Literal[ImageBuildType.notebook_ready_image]
    build_args: dict[str, str] | None = None
    base_image: str = "gcr.io/deeplearning-platform-release/base-cpu"
    requirements_txt: Path


DockerImageModel = Union[LocalBuildImageModel, ProvidedImageModel, NotebookReadyImageModel]


class DockerModel(BaseModel):
    """
    - `images`- [list[Union[LocalBuildImageModel, ProvidedImageModel, NotebookReadyImageModel]]] Docker images
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

    images: list[DockerImageModel] = Field(default_factory=list)
    repository: str | None = None
    registry: str | None = None
    cloud_build_timeout: int = 12000
    cloud_build: bool = False
    cloud_build_workerpool: str | None = None
    cloud_build_workerpool_location: str | None = None
    cloud_build_kaniko_version: str | None = "latest"
    cloud_build_kaniko_flags: list[str] = Field(
        default_factory=lambda: [
            "--cache=true",
            "--compressed-caching=false",
            "--cache-copy-layers=true",
        ]
    )

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class DockerBuildResult(BaseModel):
    name: str
    tags: list[str]
    build_type: ImageBuildType

    model_config = ConfigDict(extra="forbid")
