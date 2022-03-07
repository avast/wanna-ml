from enum import Enum
from pathlib import Path
from typing import Dict, Optional

from pydantic import (
    Extra,
    constr,
    BaseModel,
    root_validator,
)


class ContainerBuildType(str, Enum):
    custom_build_image = "custom_build_image"
    provided_image = "provided_image"
    notebook_ready_image = "notebook_ready_image"


class ContainerImageModel(BaseModel, extra=Extra.forbid, validate_assignment=True):
    name: constr(min_length=3, max_length=128)
    type: ContainerBuildType
    build_args: Optional[Dict[str, str]]
    context_dir: Optional[Path]
    dockerfile: Optional[Path]
    base_image: Optional[str]
    requirements_txt: Optional[Path]
    image_url: Optional[str]

    @root_validator
    def validate_custom_build_image(cls, values):
        if values.get("type") == "custom_build_image":
            if not (values.get("context_dir") and values.get("dockerfile")):
                raise ValueError(
                    "Both context_dir and dockerfile must be set when using custom_build_image"
                )
        return values

    @root_validator
    def validate_provided_image(cls, values):
        if values.get("type") == "provided_image":
            if not values.get("image_url"):
                raise ValueError("image_url must be set when using provided_image")
        return values

    @root_validator
    def validate_notebook_ready_image(cls, values):
        if values.get("type") == "notebook_ready_image":
            if not (values.get("base_image") and values.get("requirements_txt")):
                raise ValueError(
                    "Both base_image and requirements_txt must be set when using notebook_ready_image"
                )
        return values
