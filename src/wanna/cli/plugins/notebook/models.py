from pydantic import BaseModel, ValidationError, Extra, constr, conint, validator
from google.cloud.notebooks_v1.types.instance import Instance
from typing import Optional


class NotebookDisk(BaseModel, extra=Extra.forbid):
    disk_type: str
    size_gb: conint(ge=100, le=65535)

    @validator("disk_type")
    def validate_disk_type(cls, disk_type):
        disk_type = disk_type.upper()
        if not disk_type in Instance.DiskType.__members__:
            raise ValueError(
                f"GPU accelerator type invalid ({type}). must be on of: {Instance.DiskType._member_names_}"
            )
        return disk_type


class NotebookGPU(BaseModel, extra=Extra.forbid):
    count = 1
    accelerator_type: str

    @validator("accelerator_type")
    def validate_accelerator_type(cls, accelerator_type):
        if not accelerator_type in Instance.AcceleratorType.__members__:
            raise ValueError(
                f"GPU accelerator type invalid ({accelerator_type}). must be on of: {Instance.AcceleratorType._member_names_}"
            )
        return accelerator_type


class NotebookInstance(BaseModel, extra=Extra.forbid):
    name: constr(
        min_length=3, max_length=63, to_lower=True, regex="^[a-z][a-z0-9-]*[a-z0-9]$"
    )
    location = "europe-west4-a"
    machine_type = "n1-standard-1"
    vm_image_family = "common-cpu-notebooks"
    vm_image_project = "deeplearning-platform-release"
    container_image: Optional[str]
    tags: Optional[str]
    labels: Optional[str]
    metadata: Optional[str]
    service_account: Optional[str]
    gpu: Optional[NotebookGPU]
    boot_disk: Optional[NotebookDisk]
    data_disk: Optional[NotebookDisk]
