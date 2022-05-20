from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, EmailStr, Extra, Field, root_validator, validator

from wanna.cli.models.base_instance import BaseInstanceModel
from wanna.cli.utils.gcp import validators


class RuntimeModel(BaseInstanceModel):
    """
    The model is minimalistic before I figure out how to mount buckets into runtimes
    """

    runtime_id: str = Field(min_length=3, max_length=63, to_lower=True, regex="^[a-z][a-z0-9-]*[a-z0-9]$")
    region: str = "europe-west1"
