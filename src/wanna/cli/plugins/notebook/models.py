from pydantic import (
    BaseModel,
    ValidationError,
    Extra,
    constr,
    conint,
    validator,
    EmailStr,
    root_validator,
    FilePath,
)
from typing import Optional, Literal, List
from pathlib import Path
from wanna.cli.utils.gcp import validators


class Tensorboard(BaseModel, extra=Extra.forbid):
    enable: bool = False
    log_dir: Path


class Requirements(BaseModel, extra=Extra.forbid):
    file: Optional[FilePath]
    package_list: Optional[List[str]]

    _ = root_validator()(validators.validate_requirements)


class Network(BaseModel, extra=Extra.forbid):
    network_id: str
    subnet: Optional[str]

    _ = validator("network_id")(validators.validate_network_name)


class BucketMount(BaseModel, extra=Extra.forbid):
    remote_path: Path
    local_path: Path

    _ = validator("remote_path")(validators.validate_bucket_name)


class VMImage(BaseModel, extra=Extra.forbid):
    framework: str
    version: str
    os: Optional[str]

    _ = root_validator()(validators.validate_vm_image)


class NotebookEnvironment(BaseModel, extra=Extra.forbid):
    container_image: Optional[str]
    vm_image: Optional[VMImage]

    _ = root_validator(pre=True)(validators.validate_only_one_must_be_set)


class NotebookDisk(BaseModel, extra=Extra.forbid):
    disk_type: str
    size_gb: conint(ge=100, le=65535)

    _ = validator("disk_type")(validators.validate_disk_type)


class NotebookGPU(BaseModel, extra=Extra.forbid):
    count: Literal[1, 2, 4, 8]
    accelerator_type: str
    install_gpu_driver: bool = True

    _ = validator("accelerator_type")(validators.validate_accelerator_type)


class NotebookInstance(BaseModel, extra=Extra.forbid, validate_assignment=True):
    name: constr(
        min_length=3, max_length=63, to_lower=True, regex="^[a-z][a-z0-9-]*[a-z0-9]$"
    )
    project_id: str
    zone: str
    machine_type: str = "n1-standard-4"
    environment: NotebookEnvironment = NotebookEnvironment(vm_image=VMImage(framework="common", version="cpu"))
    tags: Optional[List[str]]
    labels: Optional[List[dict]]
    metadata: Optional[List[dict]]
    service_account: Optional[EmailStr]
    gpu: Optional[NotebookGPU]
    boot_disk: Optional[NotebookDisk]
    data_disk: Optional[NotebookDisk]
    bucket_mount: Optional[BucketMount]
    network: Optional[Network]
    tensorboard: Optional[Tensorboard]
    requirements: Optional[Requirements]

    _ = validator("project_id", allow_reuse=True)(
        validators.validate_project_id
    )
    _ = validator("zone", allow_reuse=True)(validators.validate_zone)
    _ = validator("machine_type")(validators.validate_machine_type)
