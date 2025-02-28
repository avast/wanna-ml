from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from wanna.core.utils import validators


class BaseInstanceModel(BaseModel, validate_assignment=True):
    name: str
    project_id: str
    zone: str | None = None
    region: str | None = None
    labels: dict[str, str] | None = None
    description: str | None = None
    service_account: EmailStr | None = None
    network: str | None = None
    bucket: str | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    _project_id = field_validator("project_id", mode="before")(validators.validate_project_id)
    _zone = field_validator("zone", mode="before")(validators.validate_zone)
    _region = field_validator("region", mode="before")(validators.validate_region)
    _network = field_validator("network", mode="before")(validators.validate_network_name)
    _labels = field_validator("labels", mode="before")(validators.validate_labels)
