from pydantic import Field

from wanna.core.models.base_instance import BaseInstanceModel


class TensorboardModel(BaseInstanceModel):
    name: str = Field(min_length=3, max_length=128)
    region: str
