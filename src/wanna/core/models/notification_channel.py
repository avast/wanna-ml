import sys

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

from typing import List

from pydantic import BaseModel, EmailStr, Extra


class NotificationChannelModel(BaseModel, extra=Extra.forbid):
    name: str
    type: Literal["email"]
    emails: List[EmailStr]
