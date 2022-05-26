from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr

from wanna.cli.models.cloud_scheduler import CloudSchedulerModel


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


class PushTask(BaseModel):
    manifest_artifacts: List[PathArtifact]
    container_artifacts: List[ContainerArtifact]
    json_artifacts: List[JsonArtifact]
