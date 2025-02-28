from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from wanna.core.utils import validators


class VMImage(BaseModel):
    version: str | None = None

    model_config = ConfigDict(extra="forbid")


class Disk(BaseModel):
    disk_type: str
    size_gb: int = Field(default=100, ge=100, le=65535)

    model_config = ConfigDict(extra="forbid")

    _disk_type = field_validator("disk_type")(validators.validate_disk_type)


class GPU(BaseModel):
    count: Literal[1, 2, 4, 8]
    accelerator_type: str
    install_gpu_driver: bool = True
    custom_gpu_driver_path: str | None = None

    model_config = ConfigDict(extra="forbid")

    _accelerator_type = field_validator("accelerator_type")(validators.validate_accelerator_type)
