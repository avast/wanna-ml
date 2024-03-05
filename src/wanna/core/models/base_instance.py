from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Extra, validator

from wanna.core.utils import validators


class BaseInstanceModel(BaseModel, extra=Extra.ignore, validate_assignment=True):
    name: str
    project_id: str
    zone: Optional[str]
    region: Optional[str]
    labels: Optional[Dict[str, str]]
    description: Optional[str]
    service_account: Optional[EmailStr]
    network: Optional[str]
    bucket: Optional[str]
    tags: Optional[List[str]]
    metadata: Optional[Dict[str, Any]]

    _project_id = validator("project_id", allow_reuse=True)(
        validators.validate_project_id
    )
    _zone = validator("zone", allow_reuse=True)(validators.validate_zone)
    _region = validator("region", allow_reuse=True)(validators.validate_region)
    _network = validator("network", allow_reuse=True)(validators.validate_network_name)
    _labels = validator("labels", allow_reuse=True)(validators.validate_labels)
