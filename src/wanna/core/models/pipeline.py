from pathlib import Path
from typing import Any, Optional, Union

from pydantic import Field, root_validator

from wanna.core.models.base_instance import BaseInstanceModel
from wanna.core.models.cloud_scheduler import CloudSchedulerModel


class PipelineModel(BaseInstanceModel):
    """
    - `name`- [str] Custom name for this instance
    - `project_id' - [str] (optional) Overrides GCP Project ID from the `gcp_profile` segment
    - `zone` - [str] (optional) Overrides zone from the `gcp_profile` segment
    - `region` - [str] (optional) Overrides region from the `gcp_profile` segment
    - `labels`- [dict[str, str]] (optional) Custom labels to apply to this instance
    - `service_account` - [str] (optional) Overrides service account from the `gcp_profile` segment
    - `network` - [str] (optional) Overrides network from the `gcp_profile` segment
    - `tags`- [dict[str, str]] (optional) Tags to apply to this instance
    - `metadata`- [str] (optional) Custom metadata to apply to this instance
    - `pipeline_function` - [str] (optional) Path to a cloud function
    - `pipeline_params` - [str] (optional) Path to params.yaml file
    - `docker_image_ref` - [list[str]] - list of names of docker images
    - `schedule` - [str] (optional) - Scheduler using a cron syntax
    - `tensorboard_ref` - [str] (optional) - Name of the Vertex AI Experiment
    - `notification_channels_ref` - [list[str]] (optional) list of names of notificartins channel described
    by a model: (name: str, type: Literal["email"], emails: list[EmailStr])
    - `sla_hours` - [float] (optional) Time after which the running pipeline gets stopped
    - `enable_caching` - [bool] enable KubeFlow pipeline execution caching
    """

    name: str = Field(
        min_length=3, max_length=63, to_lower=True, regex="^[a-z][a-z0-9-]*[a-z0-9]$"
    )
    zone: str
    pipeline_function: str
    pipeline_params: Union[Path, dict[str, Any], None]
    docker_image_ref: list[str] = Field(default_factory=list)
    schedule: Optional[CloudSchedulerModel]
    tensorboard_ref: Optional[str]
    network: Optional[str]
    notification_channels_ref: list[str] = Field(default_factory=list)
    sla_hours: Optional[float]
    enable_caching: bool = True
    experiment: Optional[str]

    @root_validator(pre=True)
    def set_experiment(cls, values):  # pylint: disable=no-self-argument,no-self-use
        """
        Set default pipeline experiment name based on pipeline name
        """
        experiment = values.get("experiment")
        name = values.get("name")
        if not experiment and name:
            values["experiment"] = f"{name}-experiment"

        return values
