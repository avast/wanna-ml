from pydantic import BaseModel, field_validator

from wanna.core.utils import validators


class CloudSchedulerModel(BaseModel):
    cron: str
    timezone: str = "Etc/UTC"
    service_account: str | None = None

    # Validators
    _schedule = field_validator("cron")(validators.validate_cron_schedule)


class EnvCloudSchedulerModel(CloudSchedulerModel):
    environment: str | None = None
