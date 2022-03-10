from dataclasses import dataclass, field
from typing import Dict, Optional

from serde import deserialize, serialize


@serialize
@deserialize
@dataclass
class ServiceAccount:
    account_email: str
    account_json: str


@serialize
@deserialize
@dataclass
class GCPConfig:
    project_id: str
    location: str
    region: str
    service_account: Optional[str] = field(default=None)
    labels: Dict[str, str] = field(default_factory=dict)
    settings: Dict[str, str] = field(default_factory=dict)
