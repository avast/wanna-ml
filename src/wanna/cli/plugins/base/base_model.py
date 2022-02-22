from typing import Optional

from pydantic import (
    BaseModel,
    Extra,
    validator,
)
from wanna.cli.utils.gcp import validators


class BaseInstanceModel(BaseModel, extra=Extra.forbid, validate_assignment=True):
    name: str
    project_id: str
    zone: Optional[str]
    region: Optional[str]

    _ = validator("project_id", allow_reuse=True)(validators.validate_project_id)
    _ = validator("zone", allow_reuse=True)(validators.validate_zone)
    _ = validator("region", allow_reuse=True)(validators.validate_region)
