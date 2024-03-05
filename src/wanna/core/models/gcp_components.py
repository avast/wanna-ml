import sys
from typing import Optional

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

from pydantic import BaseModel, Extra, Field, validator

from wanna.core.utils import validators


class VMImage(BaseModel, extra=Extra.forbid):
    framework: str
    version: str
    os: Optional[str] = None

    # _ = root_validator()(validators.validate_vm_image)


class Disk(BaseModel, extra=Extra.forbid):
    disk_type: str
    size_gb: int = Field(ge=100, le=65535, default=100)

    _disk_type = validator("disk_type")(validators.validate_disk_type)


class GPU(BaseModel, extra=Extra.forbid):
    count: Literal[1, 2, 4, 8]
    accelerator_type: str
    install_gpu_driver: bool = True

    _accelerator_type = validator("accelerator_type")(
        validators.validate_accelerator_type
    )
