from typing import Optional, Dict

from pydantic import (
    BaseModel,
    EmailStr,
    Extra,
    validator,
)
from wanna.cli.utils.gcp import validators


class BaseInstanceModel(BaseModel, extra=Extra.forbid, validate_assignment=True):
    name: str
    project_id: str
    zone: Optional[str]
    region: Optional[str]
    labels: Optional[Dict[str, str]]
    description: Optional[str]
    service_account: Optional[EmailStr]
    bucket: Optional[str]

    _project_id = validator("project_id", allow_reuse=True)(
        validators.validate_project_id
    )
    _zone = validator("zone", allow_reuse=True)(validators.validate_zone)
    _region = validator("region", allow_reuse=True)(validators.validate_region)
