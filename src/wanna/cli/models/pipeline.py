from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import Field, validator

from wanna.cli.models.base_instance import BaseInstanceModel
from wanna.cli.utils.gcp import validators


class PipelineModel(BaseInstanceModel):
    name: str = Field(min_length=3, max_length=63, to_lower=True, regex="^[a-z][a-z0-9-]*[a-z0-9]$")
    zone: str
    pipeline_file: str
    pipeline_function: Optional[str]
    pipeline_params: Union[Path, Dict[str, Any], None]
    tags: Optional[List[str]]
    metadata: Optional[List[Dict[str, Any]]]
    docker_image_ref: Optional[List[str]]
    schedule: Optional[str]

    # Validators
    _schedule = validator("schedule")(validators.validate_cron_schedule)
