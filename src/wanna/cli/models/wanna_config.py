from typing import List, Optional

from pydantic import Extra, BaseModel, validator
from wanna.cli.models.docker import DockerModel
from wanna.cli.models.gcp_settings import GCPSettingsModel
from wanna.cli.models.notebook import NotebookModel
from wanna.cli.models.tensorboard import TensorboardModel
from wanna.cli.models.training_custom_job import TrainingCustomJobModel
from wanna.cli.models.wanna_project import WannaProjectModel
from wanna.cli.utils.config_enricher import enrich_instance_with_gcp_settings


class WannaConfigModel(BaseModel, extra=Extra.forbid, validate_assignment=True):
    wanna_project: WannaProjectModel
    gcp_settings: GCPSettingsModel
    docker: Optional[DockerModel]
    notebooks: Optional[List[NotebookModel]]
    tensorboards: Optional[List[TensorboardModel]]
    training_custom_jobs: Optional[List[TrainingCustomJobModel]]

    _notebooks = validator("notebooks", pre=True, each_item=True, allow_reuse=True)(
        enrich_instance_with_gcp_settings
    )
    _tensorboards = validator(
        "tensorboards", pre=True, each_item=True, allow_reuse=True
    )(enrich_instance_with_gcp_settings)
    _training_custom_jobs = validator(
        "training_custom_jobs", pre=True, each_item=True, allow_reuse=True
    )(enrich_instance_with_gcp_settings)

    @validator("notebooks", pre=True, each_item=True, allow_reuse=True)
    def validate_docker_images_defined(cls, values_inst, values):
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
