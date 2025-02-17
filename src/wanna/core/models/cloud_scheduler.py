from typing import Optional

from pydantic import BaseModel, field_validator

from wanna.core.utils import validators


class CloudSchedulerModel(BaseModel):
    cron: str
    timezone: str = "Etc/UTC"
    service_account: Optional[str] = None

    # Validators
    _schedule = field_validator("cron")(validators.validate_cron_schedule)
