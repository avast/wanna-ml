from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from wanna.cli.models.base_instance import BaseInstanceModel
from wanna.cli.models.cloud_scheduler import CloudSchedulerModel
from wanna.cli.models.docker import DockerBuildResult


class PipelineModel(BaseInstanceModel):
    name: str = Field(min_length=3, max_length=63, to_lower=True, regex="^[a-z][a-z0-9-]*[a-z0-9]$")
    zone: str
    pipeline_file: str
    pipeline_function: Optional[str]
    pipeline_params: Union[Path, Dict[str, Any], None]
    tags: Optional[List[str]]
    metadata: Optional[List[Dict[str, Any]]]
    docker_image_ref: Optional[List[str]]
    schedule: Optional[CloudSchedulerModel]
    tensorboard_ref: Optional[str]


class PipelineDeployment(BaseModel, arbitrary_types_allowed=True):
    pipeline_name: str
    pipeline_root: str
    json_spec_path: str
    parameter_values: Dict[str, Any] = {}
    labels: Dict[str, str] = {}
    enable_caching: bool = True
    project: Optional[str]
    location: Optional[str]
    service_account: Optional[str]
    schedule: Optional[CloudSchedulerModel]
    docker_refs: List[DockerBuildResult]
    compile_env_params: Dict[str, str]
