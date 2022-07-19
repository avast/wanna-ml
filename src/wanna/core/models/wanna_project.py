from typing import List, Optional

from pydantic import BaseModel, EmailStr, Extra


class WannaProjectModel(BaseModel, extra=Extra.forbid):
    name: str
    version: str
    authors: List[EmailStr]
    billing_id: Optional[str]
    organization_id: Optional[str]
