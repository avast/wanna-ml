from pydantic import (
    Extra,
    constr,
)
from wanna.cli.models.base_instance import BaseInstanceModel


class TensorboardModel(BaseInstanceModel, extra=Extra.forbid, validate_assignment=True):
    name: constr(min_length=3, max_length=128)
    region: str
