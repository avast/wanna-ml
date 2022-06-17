from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import Field

from wanna.core.models.base_instance import BaseInstanceModel
from wanna.core.models.cloud_scheduler import CloudSchedulerModel


class PipelineModel(BaseInstanceModel):
    name: str = Field(min_length=3, max_length=63, to_lower=True, regex="^[a-z][a-z0-9-]*[a-z0-9]$")
    zone: str
    pipeline_file: str
    pipeline_function: Optional[str]
    pipeline_params: Union[Path, Dict[str, Any], None]
    docker_image_ref: List[str] = []
    schedule: Optional[CloudSchedulerModel]
    tensorboard_ref: Optional[str]
    network: Optional[str]
    notification_channels_ref: List[str] = []
