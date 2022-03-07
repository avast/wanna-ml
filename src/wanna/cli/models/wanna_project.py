from pydantic import (
    BaseModel,
    EmailStr,
    Extra,
)
from typing import List


class WannaProjectModel(BaseModel, extra=Extra.forbid):
    name: str
    version: str
    authors: List[EmailStr]
