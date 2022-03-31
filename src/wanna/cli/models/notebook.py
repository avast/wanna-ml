from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, EmailStr, Extra, Field, root_validator, validator

from wanna.cli.models.base_instance import BaseInstanceModel
from wanna.cli.utils.gcp import validators


class Network(BaseModel, extra=Extra.forbid):
    network_id: str
    subnet: Optional[str]

    _network_id = validator("network_id")(validators.validate_network_name)


class BucketMount(BaseModel, extra=Extra.forbid):
    bucket_name: str
    bucket_dir: Path
    local_path: Path

    _bucket_name = validator("bucket_name")(validators.validate_bucket_name)


class VMImage(BaseModel, extra=Extra.forbid):
    framework: str
    version: str
    os: Optional[str]

    # _ = root_validator()(validators.validate_vm_image)


class NotebookEnvironment(BaseModel, extra=Extra.forbid):
    vm_image: Optional[VMImage]
    docker_image_ref: Optional[str]

    _ = root_validator()(validators.validate_only_one_must_be_set)


class NotebookDisk(BaseModel, extra=Extra.forbid):
    disk_type: str
    size_gb: int = Field(ge=100, le=65535)

    _disk_type = validator("disk_type")(validators.validate_disk_type)


class NotebookGPU(BaseModel, extra=Extra.forbid):
    count: Literal[1, 2, 4, 8]
    accelerator_type: str
    install_gpu_driver: bool = True

    _accelerator_type = validator("accelerator_type")(validators.validate_accelerator_type)


class NotebookModel(BaseInstanceModel):
    name: str = Field(min_length=3, max_length=63, to_lower=True, regex="^[a-z][a-z0-9-]*[a-z0-9]$")
    zone: str
    machine_type: str = "n1-standard-4"
    environment: NotebookEnvironment = NotebookEnvironment(vm_image=VMImage(framework="common", version="cpu"))
    tags: Optional[List[str]]
    metadata: Optional[List[Dict[str, str]]]
    service_account: Optional[EmailStr]
    instance_owner: Optional[EmailStr]
    gpu: Optional[NotebookGPU]
    boot_disk: Optional[NotebookDisk]
    data_disk: Optional[NotebookDisk]
    bucket_mounts: Optional[List[BucketMount]]
    network: Optional[Network]
    tensorboard_ref: Optional[str]

    _machine_type = validator("machine_type")(validators.validate_machine_type)
