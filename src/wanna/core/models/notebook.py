from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Extra, Field, root_validator, validator

from wanna.core.models.base_instance import BaseInstanceModel
from wanna.core.models.gcp_components import GPU, Disk, VMImage
from wanna.core.utils import validators


class BucketMount(BaseModel, extra=Extra.forbid):
    bucket_name: str
    bucket_dir: Path
    local_path: Path

    _bucket_name = validator("bucket_name")(validators.validate_bucket_name)


class NotebookEnvironment(BaseModel, extra=Extra.forbid):
    vm_image: Optional[VMImage]
    docker_image_ref: Optional[str]

    _ = root_validator()(validators.validate_only_one_must_be_set)


class NotebookModel(BaseInstanceModel):
    name: str = Field(min_length=3, max_length=63, to_lower=True, regex="^[a-z][a-z0-9-]*[a-z0-9]$")
    zone: str
    machine_type: str = "n1-standard-4"
    environment: NotebookEnvironment = NotebookEnvironment(vm_image=VMImage(framework="common", version="cpu"))
    instance_owner: Optional[EmailStr]
    gpu: Optional[GPU]
    boot_disk: Optional[Disk]
    data_disk: Optional[Disk]
    bucket_mounts: Optional[List[BucketMount]]
    network: Optional[str]
    subnet: Optional[str]
    tensorboard_ref: Optional[str]

    _machine_type = validator("machine_type")(validators.validate_machine_type)


class ManagedNotebookModel(BaseInstanceModel):
    name: str = Field(min_length=3, max_length=63, to_lower=True, regex="^[a-z][a-z0-9-]*[a-z0-9]$")
    owner: str
    machine_type: Optional[str] = "n1-standard-4"
    gpu: Optional[GPU]
    data_disk: Optional[Disk]
    kernels: Optional[List[str]]
    tensorboard_ref: Optional[str]
    network: Optional[str]
    subnet: Optional[str]
    internal_ip_only: Optional[bool] = True
    idle_shutdown: Optional[bool]
    idle_shutdown_timeout: Optional[int] = Field(ge=10, le=1440)
