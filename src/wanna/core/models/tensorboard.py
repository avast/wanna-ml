from pydantic import Field

from wanna.core.models.base_instance import BaseInstanceModel


class TensorboardModel(BaseInstanceModel):
    """
    - `name`- [str] Custom name for this instance
    - `project_id` - [str] (optional) Overrides GCP Project ID from the `gcp_profile` segment
    - `region` - [str] (optional) Overrides region from the `gcp_profile` segment
    - `description` - [str] (optional) Tensorboard description to be shown in the UI
    - `labels`- [Dict[str, str]] (optional) Custom labels to apply to this instance
    """

    name: str = Field(min_length=3, max_length=128)
    region: str
