from enum import Enum
from pathlib import Path
from typing import Any, Generic, Literal, TypeVar, Union

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from wanna.core.models.cloud_scheduler import CloudSchedulerModel, EnvCloudSchedulerModel
from wanna.core.models.docker import DockerBuildResult
from wanna.core.models.notification_channel import NotificationChannelModel
from wanna.core.models.training_custom_job import JobModelTypeAlias

PipelineEnvParams = dict[str, Union[str, None, EmailStr]]


class GCPResource(BaseModel):
    name: str
    project: str
    location: str
    service_account: str | None = None

    model_config = ConfigDict(
        extra="forbid", validate_assignment=True, arbitrary_types_allowed=True
    )

    def get_base_resource(self):
        return self.model_dump()


class NotificationChannelResource(GCPResource):
    type_: Literal["email", "pubsub"]
    config: dict[str, str]
    labels: dict[str, str]
    description: str | None = None


class CloudSchedulerResource(GCPResource):
    cloud_scheduler: CloudSchedulerModel
    body: dict[str, Any]
    labels: dict[str, str]
    notification_channels: list[str]


class CloudFunctionResource(GCPResource):
    build_dir: Path
    resource_root: str
    resource_function_template: str
    resource_requirements_template: str
    template_vars: dict[str, Any]
    env_params: PipelineEnvParams
    labels: dict[str, str]
    network: str | None = None
    notification_channels: list[str]


class LogMetricResource(GCPResource):
    filter_: str
    description: str


class AlertPolicyResource(GCPResource):
    logging_metric_type: str
    resource_type: str
    display_name: str
    labels: dict[str, str]
    notification_channels: list[str]


class PipelineResource(GCPResource):
    pipeline_name: str
    pipeline_bucket: str
    pipeline_root: str
    pipeline_version: str
    json_spec_path: str
    parameter_values: dict[str, Any] = Field(default_factory=dict)
    labels: dict[str, str] = Field(default_factory=dict)
    enable_caching: bool = True
    schedule: CloudSchedulerModel | list[EnvCloudSchedulerModel] | None
    docker_refs: list[DockerBuildResult]
    compile_env_params: PipelineEnvParams
    network: str | None = None
    notification_channels: list[NotificationChannelModel] = Field(default_factory=list)
    encryption_spec_key_name: str | None = None
    experiment: str | None = None


# BaseCustomJobModel
JOB = TypeVar("JOB", bound=JobModelTypeAlias)  # dependency from wanna models


class JobResource(GCPResource, Generic[JOB]):
    job_payload: dict[str, Any]
    image_refs: list[str] = Field(default_factory=list)
    tensorboard: str | None = None
    network: str | None = None
    job_config: JOB
    encryption_spec: str | None = None
    environment_variables: dict[str, str] | None = None


class PushArtifact(BaseModel):
    name: str


class JsonArtifact(PushArtifact):
    name: str
    json_body: dict[Any, Any]
    destination: str


class PathArtifact(PushArtifact):
    name: str
    source: str
    destination: str


class ContainerArtifact(PushArtifact):
    name: str
    tags: list[str]


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
    manifest_artifacts: list[PathArtifact]
    container_artifacts: list[ContainerArtifact]
    json_artifacts: list[JsonArtifact]


PushResult = list[tuple[list[ContainerArtifact], list[PathArtifact], list[JsonArtifact]]]
