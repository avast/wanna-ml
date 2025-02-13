from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from wanna.core.utils import validators


class BaseInstanceModel(BaseModel, validate_assignment=True):
    name: str
    project_id: str
    zone: Optional[str] = None
    region: Optional[str] = None
    labels: Optional[dict[str, str]] = None
    description: Optional[str] = None
    service_account: Optional[EmailStr] = None
    network: Optional[str] = None
    bucket: Optional[str] = None
    tags: Optional[list[str]] = None
    metadata: Optional[dict[str, Any]] = None

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    _project_id = field_validator("project_id", mode="before")(validators.validate_project_id)
    _zone = field_validator("zone", mode="before")(validators.validate_zone)
    _region = field_validator("region", mode="before")(validators.validate_region)
    _network = field_validator("network", mode="before")(validators.validate_network_name)
    _labels = field_validator("labels", mode="before")(validators.validate_labels)
