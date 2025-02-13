from typing import Annotated, Optional, Union

from pydantic import BaseModel, BeforeValidator, Field

from wanna.core.models.docker import DockerModel
from wanna.core.models.gcp_profile import GCPProfileModel
from wanna.core.models.notification_channel import NotificationChannelModel
from wanna.core.models.pipeline import PipelineModel
from wanna.core.models.tensorboard import TensorboardModel
from wanna.core.models.training_custom_job import CustomJobModel, TrainingCustomJobModel
from wanna.core.models.wanna_project import WannaProjectModel
from wanna.core.models.workbench import InstanceModel
from wanna.core.utils.config_enricher import (
    enrich_instance_with_gcp_settings_v2,
)
from wanna.core.utils.validators import validate_docker_images_defined


class WannaConfigModel(BaseModel, validate_assignment=True):
    wanna_project: WannaProjectModel
    gcp_profile: GCPProfileModel
    docker: Optional[DockerModel] = None
    tensorboards: list[
        Annotated[TensorboardModel, BeforeValidator(enrich_instance_with_gcp_settings_v2)]
    ] = Field(default_factory=list)
    jobs: list[
        Annotated[
            Union[CustomJobModel, TrainingCustomJobModel],
            BeforeValidator(enrich_instance_with_gcp_settings_v2),
        ]
    ] = Field(default_factory=list)
    pipelines: list[
        Annotated[PipelineModel, BeforeValidator(enrich_instance_with_gcp_settings_v2)]
    ] = Field(default_factory=list)
    notebooks: list[
        Annotated[
            InstanceModel,
            BeforeValidator(validate_docker_images_defined),
            BeforeValidator(enrich_instance_with_gcp_settings_v2),
        ]
    ] = Field(default_factory=list)
    notification_channels: list[NotificationChannelModel] = Field(default_factory=list)
