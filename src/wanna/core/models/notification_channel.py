from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, EmailStr, Field


class BaseNotificationChannel(BaseModel):
    """
    Base class for multiple GCP notification channels types

    :param str name: Friendly name for the channel
    :param Optional[str] description: Short description of the channel
    """

    name: str
    description: str | None = None


class EmailNotificationChannel(BaseNotificationChannel):
    """
    EmailNotificationChannel GCP notification channel type

    :param str type: The type of channel that will be created
    :param list[str] emails: the emails to which the alerts will be sent
    """

    type: Literal["email"]
    emails: list[EmailStr]


class PubSubNotificationChannel(BaseNotificationChannel):
    """
    PubsubNotificationChannel GCP notification channel type

    :param str type: The type of channel that will be created
    :param list[str] topics: the pubsub topic to which the alerts will be sent
    """

    type: Literal["pubsub"]
    topics: list[str]


NotificationChannelModel = Annotated[
    Union[EmailNotificationChannel, PubSubNotificationChannel],
    Field(discriminator="type"),
]
