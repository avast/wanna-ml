from typing import Optional

from pydantic import BaseModel, validator

from wanna.cli.utils.gcp import validators


class CloudSchedulerModel(BaseModel):
    cron: str
    timezone: str = "Etc/UTC"
    service_account: Optional[str]

    # Validators
    _schedule = validator("cron")(validators.validate_cron_schedule)
