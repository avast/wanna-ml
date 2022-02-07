from pydantic import BaseModel, Extra, validator
from typing import Optional

from wanna.cli.utils.gcp import validators


class WannaProject(BaseModel, extra=Extra.forbid):
    name: str
    version: int


class GCPSettings(BaseModel, extra=Extra.forbid):
    project_id: str
    zone: str
    labels: Optional[str]
    service_account: Optional[str]

    _ = validator("project_id", allow_reuse=True)(validators.validate_project_id)
    _ = validator("zone", allow_reuse=True)(validators.validate_zone)
