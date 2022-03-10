from dataclasses import dataclass, field
from typing import List

from serde import deserialize

from wanna.cli.gcloud.models import GCPConfig
from wanna.cli.plugins.job.models import JobConfig


@deserialize
@dataclass
class WannaFile:
    project_name: str
    gcp: GCPConfig
    jobs: List[JobConfig] = field(default_factory=[])
    schema: str = field(default_factory="v1")
