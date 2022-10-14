import sys

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

from enum import Enum
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar

from pydantic import BaseModel, EmailStr, Extra
from pydantic.generics import GenericModel

from wanna.core.models.cloud_scheduler import CloudSchedulerModel
from wanna.core.models.docker import DockerBuildResult
from wanna.core.models.notification_channel import NotificationChannelModel
from wanna.core.models.training_custom_job import BaseCustomJobModel


class GCPResource(GenericModel, extra=Extra.forbid, validate_assignment=True, arbitrary_types_allowed=True):
    name: str
    project: str
    location: str
    service_account: Optional[EmailStr]

    def get_base_resource(self):
        return self.dict()


class NotificationChannelResource(GCPResource):
    type_: Literal["email"]
    config: Dict[str, str]
    labels: Dict[str, str]


class CloudSchedulerResource(GCPResource):
    cloud_scheduler: CloudSchedulerModel
    body: Dict[str, Any]
    labels: Dict[str, str]
    notification_channels: List[str]


class CloudFunctionResource(GCPResource):
    build_dir: Path
    resource_root: str
    resource_function_template: str
    resource_requirements_template: str
    template_vars: Dict[str, Any]
    env_params: Dict[str, str]
    labels: Dict[str, str]
    network: str
    notification_channels: List[str]


class LogMetricResource(GCPResource):
    filter_: str
    description: str


class AlertPolicyResource(GCPResource):
    logging_metric_type: str
    resource_type: str
    display_name: str
    labels: Dict[str, str]
    notification_channels: List[str]


class PipelineResource(GCPResource):
    pipeline_name: str
    pipeline_bucket: str
    pipeline_root: str
    pipeline_version: str
    json_spec_path: str
    parameter_values: Dict[str, Any] = {}
    labels: Dict[str, str] = {}
    enable_caching: bool = True
    schedule: Optional[CloudSchedulerModel]
    docker_refs: List[DockerBuildResult]
    compile_env_params: Dict[str, str]
    network: str
    notification_channels: List[NotificationChannelModel] = []
    encryption_spec_key_name: Optional[str]


JOB = TypeVar("JOB", bound=BaseCustomJobModel, covariant=True)  # dependency from wanna models


class JobResource(GCPResource, Generic[JOB]):
    job_payload: Dict[str, Any]
    image_refs: List[str] = []
    tensorboard: Optional[str]
    network: Optional[str]
    job_config: JOB
    encryption_spec: Optional[str]
    environment_variables: Optional[Dict[str, str]]


class PushArtifact(BaseModel):
    name: str


class JsonArtifact(PushArtifact):
    name: str
    json_body: Dict[Any, Any]
    destination: str


class PathArtifact(PushArtifact):
    name: str
    source: str
    destination: str


class ContainerArtifact(PushArtifact):
    name: str
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


PushResult = List[Tuple[List[ContainerArtifact], List[PathArtifact], List[JsonArtifact]]]
