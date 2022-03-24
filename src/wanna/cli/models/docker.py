from enum import Enum
from pathlib import Path
from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Extra, Field


class ImageBuildType(str, Enum):
    local_build_image = "local_build_image"
    provided_image = "provided_image"
    notebook_ready_image = "notebook_ready_image"


class LocalBuildImageModel(BaseModel, extra=Extra.forbid, validate_assignment=True):
    name: str = Field(min_length=3, max_length=128)
    build_type: Literal[ImageBuildType.local_build_image]
    build_args: Optional[Dict[str, str]]
    context_dir: Path
    dockerfile: Path


class ProvidedImageModel(BaseModel, extra=Extra.forbid, validate_assignment=True):
    name: str = Field(min_length=3, max_length=128)
    build_type: Literal[ImageBuildType.provided_image]
    image_url: str


class NotebookReadyImageModel(BaseModel, extra=Extra.forbid, validate_assignment=True):
    name: str = Field(min_length=3, max_length=128)
    build_type: Literal[ImageBuildType.notebook_ready_image]
    build_args: Optional[Dict[str, str]]
    base_image: str = "gcr.io/deeplearning-platform-release/base-cpu"
    requirements_txt: Path


DockerImageModel = Union[LocalBuildImageModel, ProvidedImageModel, NotebookReadyImageModel]


class DockerModel(BaseModel, extra=Extra.forbid, validate_assignment=True):
    images: List[DockerImageModel]
