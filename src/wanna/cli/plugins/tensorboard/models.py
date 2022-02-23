from pydantic import (
    Extra,
    constr,
    validator,
)
from wanna.cli.plugins.base.models import BaseInstanceModel
from wanna.cli.utils.gcp import validators


class TensorboardModel(BaseInstanceModel, extra=Extra.forbid, validate_assignment=True):
    name: constr(min_length=3, max_length=128)
    region: str

    _ = validator("region", allow_reuse=True)(validators.validate_region)
