from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr

from wanna.core.models.cloud_scheduler import CloudSchedulerModel


class CloudSchedulerResource(BaseModel):
    name: str
    project: str
    location: str
    cloud_scheduler: CloudSchedulerModel
    service_account: Optional[EmailStr]
    body: Dict[str, Any]


class CloudFunctionResource(BaseModel):
    name: str
    project: str
    location: str
    service_account: str
    build_dir: Path
    resource_root: str
    resource_function_template: str
    resource_requirements_template: str
    template_vars: Dict[str, Any]
    labels: Dict[str, str]


class DeploymentArtifact(BaseModel):
    title: str


class JsonArtifact(DeploymentArtifact):
    title: str
    json_body: Dict[Any, Any]
    destination: str


class PathArtifact(DeploymentArtifact):
    title: str
    source: str
    destination: str


class ContainerArtifact(DeploymentArtifact):
    title: str
    tags: List[str]


class PushMode(str, Enum):
    all = "all"
    manifests = "manifests"
    containers = "containers"
    quick = "quick"

    def is_quick_mode(self) -> bool:
        return self == PushMode.manifests or self == PushMode.quick

    def can_push_containers(self) -> bool:
        return self == PushMode.all or self == PushMode.containers

    def can_push_gcp_resources(self) -> bool:
        return self == PushMode.all or self == PushMode.manifests


class PushTask(BaseModel):
    manifest_artifacts: List[PathArtifact]
    container_artifacts: List[ContainerArtifact]
    json_artifacts: List[JsonArtifact]
