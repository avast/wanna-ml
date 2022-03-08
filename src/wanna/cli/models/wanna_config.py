from typing import List, Optional

from pydantic import Extra, BaseModel, validator
from wanna.cli.models.docker import DockerModel
from wanna.cli.models.gcp_settings import GCPSettingsModel
from wanna.cli.models.notebook import NotebookModel
from wanna.cli.models.tensorboard import TensorboardModel
from wanna.cli.models.wanna_project import WannaProjectModel
from wanna.cli.utils.config_enricher import enrich_instance_with_gcp_settings


class WannaConfigModel(BaseModel, extra=Extra.forbid, validate_assignment=True):
    wanna_project: WannaProjectModel
    gcp_settings: GCPSettingsModel
    docker: Optional[DockerModel]
    notebooks: Optional[List[NotebookModel]]
    tensorboards: Optional[List[TensorboardModel]]

    _notebooks = validator("notebooks", pre=True, each_item=True, allow_reuse=True)(
        enrich_instance_with_gcp_settings
    )
    _tensorboards = validator(
        "tensorboards", pre=True, each_item=True, allow_reuse=True
    )(enrich_instance_with_gcp_settings)
