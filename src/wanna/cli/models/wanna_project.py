from pydantic import (
    BaseModel,
    EmailStr,
    Extra,
)


class WannaProjectModel(BaseModel, extra=Extra.forbid):
    name: str
    version: float
    author: EmailStr
