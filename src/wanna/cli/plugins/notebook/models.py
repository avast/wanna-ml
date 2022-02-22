from pathlib import Path
from typing import Optional, Literal, List, Dict
from wanna.cli.plugins.base.base_model import BaseInstanceModel

from pydantic import (
    BaseModel,
    Extra,
    constr,
    conint,
    validator,
    EmailStr,
    root_validator,
)
from wanna.cli.utils.gcp import validators


class CustomPythonContainer(BaseModel, extra=Extra.forbid):
    base_image: str = (
        "gcr.io/deeplearning-platform-release/base-cpu"  # TODO: change to avast mirror
    )
    requirements_file: Path
    build_options: Optional[List[Dict]]

    _ = root_validator()(validators.validate_requirements)


class Network(BaseModel, extra=Extra.forbid):
    network_id: str
    subnet: Optional[str]

    _ = validator("network_id")(validators.validate_network_name)


class BucketMount(BaseModel, extra=Extra.forbid):
    bucket_name: str
    bucket_dir: Path
    local_path: Path

    _ = validator("bucket_name")(validators.validate_bucket_name)


class VMImage(BaseModel, extra=Extra.forbid):
    framework: str
    version: str
    os: Optional[str]

    _ = root_validator()(validators.validate_vm_image)


class NotebookEnvironment(BaseModel, extra=Extra.forbid):
    container_image: Optional[str]
    vm_image: Optional[VMImage]
    custom_python_container: Optional[CustomPythonContainer]

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


class NotebookModel(BaseInstanceModel, extra=Extra.forbid, validate_assignment=True):
    name: constr(
        min_length=3, max_length=63, to_lower=True, regex="^[a-z][a-z0-9-]*[a-z0-9]$"
    )
    project_id: str
    zone: str
    machine_type: str = "n1-standard-4"
    environment: NotebookEnvironment = NotebookEnvironment(
        vm_image=VMImage(framework="common", version="cpu")
    )
    tags: Optional[List[str]]
    labels: Optional[Dict[str, str]]
    metadata: Optional[List[Dict]]
    service_account: Optional[EmailStr]
    open_to_other_users: bool = False
    instance_owner: Optional[EmailStr]
    gpu: Optional[NotebookGPU]
    boot_disk: Optional[NotebookDisk]
    data_disk: Optional[NotebookDisk]
    bucket_mounts: Optional[List[BucketMount]]
    network: Optional[Network]

    _ = validator("project_id", allow_reuse=True)(validators.validate_project_id)
    _ = validator("zone", allow_reuse=True)(validators.validate_zone)
    _ = validator("machine_type")(validators.validate_machine_type)
