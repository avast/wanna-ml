from typing import List, Optional, Union

from pydantic import BaseModel, Extra, validator

from wanna.core.models.docker import DockerModel
from wanna.core.models.gcp_profile import GCPProfileModel
from wanna.core.models.notebook import ManagedNotebookModel, NotebookModel
from wanna.core.models.notification_channel import NotificationChannelModel
from wanna.core.models.pipeline import PipelineModel
from wanna.core.models.tensorboard import TensorboardModel
from wanna.core.models.training_custom_job import CustomJobModel, TrainingCustomJobModel
from wanna.core.models.wanna_project import WannaProjectModel
from wanna.core.utils.config_enricher import enrich_instance_with_gcp_settings


class WannaConfigModel(BaseModel, extra=Extra.forbid, validate_assignment=True):
    wanna_project: WannaProjectModel
    gcp_profile: GCPProfileModel
    docker: Optional[DockerModel]
    notebooks: List[NotebookModel] = []
    tensorboards: List[TensorboardModel] = []
    jobs: List[Union[CustomJobModel, TrainingCustomJobModel]] = []
    pipelines: List[PipelineModel] = []
    managed_notebooks: List[ManagedNotebookModel] = []
    notification_channels: List[NotificationChannelModel] = []

    _notebooks = validator("notebooks", pre=True, each_item=True, allow_reuse=True)(
        enrich_instance_with_gcp_settings
    )
    _managed_notebooks = validator(
        "managed_notebooks", pre=True, each_item=True, allow_reuse=True
    )(enrich_instance_with_gcp_settings)
    _tensorboards = validator(
        "tensorboards", pre=True, each_item=True, allow_reuse=True
    )(enrich_instance_with_gcp_settings)
    _jobs = validator("jobs", pre=True, each_item=True, allow_reuse=True)(
        enrich_instance_with_gcp_settings
    )
    _pipelines = validator("pipelines", pre=True, each_item=True, allow_reuse=True)(
        enrich_instance_with_gcp_settings
    )

    # TODO:
    # _gcp_profile = validator("gcp_profile", pre=True, allow_reuse=True)(enrich_gcp_profile_with_wanna_default_labels)

    @validator("notebooks", pre=True, each_item=True, allow_reuse=True)
    def validate_docker_images_defined(
        cls, values_inst, values
    ):  # pylint: disable=no-self-argument,no-self-use
        docker_image_ref = values_inst.get("environment", {}).get("docker_image_ref")
        if docker_image_ref:
            if not values.get("docker"):
                raise ValueError(
                    f"Docker image with name {docker_image_ref} is not defined"
                )
            defined_images = [i.name for i in values.get("docker").images]
            if docker_image_ref not in defined_images:
                raise ValueError(
                    f"Docker image with name {docker_image_ref} is not defined"
                )
        return values_inst
