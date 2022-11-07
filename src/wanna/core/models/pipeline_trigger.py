from typing import Optional

from pydantic import BaseModel, validator

from wanna.core.utils import validators


class CloudSchedulerModel(BaseModel):
    cron: str
    timezone: str = "Etc/UTC"
    service_account: Optional[str]

    # Validators
    _schedule = validator("cron")(validators.validate_cron_schedule)


class GCSNotificationModel(BaseModel):
    bucket: str
    event_type: str = "OBJECT_FINALIZE"
    blob_name_prefix: Optional[str]


class PipelineTriggerModel(BaseModel):
    schedule: Optional[CloudSchedulerModel]
    gcs: Optional[GCSNotificationModel]