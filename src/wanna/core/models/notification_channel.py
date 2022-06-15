import sys
if sys.version_info >= (3, 8):
    from typing import Literal, List
else:
    from typing_extensions import Literal

from pydantic import BaseModel, Extra, EmailStr

class NotificationChannel(BaseModel, extra=Extra.forbid):
    type: Literal['email']
    emails: List[EmailStr]