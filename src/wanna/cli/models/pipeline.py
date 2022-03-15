from pathlib import Path
from typing import Dict, List, Optional, Union

from pydantic import Extra, constr, validator

from wanna.cli.models.base_instance import BaseInstanceModel
from wanna.cli.utils.gcp import validators


class PipelineModel(BaseInstanceModel, extra=Extra.forbid, validate_assignment=True):
    name: constr(min_length=3, max_length=63, to_lower=True, regex="^[a-z][a-z0-9-]*[a-z0-9]$")
    zone: str
    pipeline_file: str
    pipeline_function: Optional[str]
    pipeline_params: Union[Path, dict, None]
    tags: Optional[List[str]]
    metadata: Optional[List[Dict]]
    docker_image_ref: Optional[List[str]]
    schedule: Optional[str]

    # Validators
    _schedule = validator("schedule")(validators.validate_cron_schedule)
