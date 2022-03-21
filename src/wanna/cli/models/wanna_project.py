from typing import List

from pydantic import BaseModel, EmailStr, Extra


class WannaProjectModel(BaseModel, extra=Extra.forbid):
    name: str
    version: str
    authors: List[EmailStr]
