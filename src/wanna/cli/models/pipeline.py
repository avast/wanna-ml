from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field, validator
from python_on_whales import Image

from wanna.cli.models.base_instance import BaseInstanceModel
from wanna.cli.models.docker import DockerImageModel
from wanna.cli.utils.gcp import validators


class PipelineScheduleModel(BaseModel):
    cron: str
    timezone: str = "Etc/UTC"

    # Validators
    _schedule = validator("cron")(validators.validate_cron_schedule)


class PipelineModel(BaseInstanceModel):
    name: str = Field(min_length=3, max_length=63, to_lower=True, regex="^[a-z][a-z0-9-]*[a-z0-9]$")
    zone: str
    pipeline_file: str
    pipeline_function: Optional[str]
    pipeline_params: Union[Path, Dict[str, Any], None]
    tags: Optional[List[str]]
    metadata: Optional[List[Dict[str, Any]]]
    docker_image_ref: Optional[List[str]]
    schedule: Optional[PipelineScheduleModel]
    tensorboard_ref: Optional[str]


class PipelineMeta(BaseModel, arbitrary_types_allowed=True):
    json_spec_path: Path
    config: PipelineModel
    images: List[Tuple[DockerImageModel, Optional[Image], str]]
    parameter_values: Dict[str, Any]
    compile_env_params: Dict[str, str]


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
    schedule: Optional[PipelineScheduleModel]
