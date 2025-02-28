from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Extra,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from wanna.core.models.base_instance import BaseInstanceModel
from wanna.core.models.gcp_components import GPU, Disk, VMImage
from wanna.core.utils import validators

WorkbenchName = Annotated[
    str,
    StringConstraints(
        min_length=3, max_length=63, pattern="^[a-z][a-z0-9-]*[a-z0-9]$", to_lower=True
    ),
]


class BucketMount(BaseModel, extra=Extra.forbid):
    bucket_name: str
    mount_path: str = "/gcs"

    model_config = ConfigDict(extra="forbid")

    _bucket_name = field_validator("bucket_name")(validators.validate_bucket_name)


class NotebookEnvironment(BaseModel, extra=Extra.forbid):
    vm_image: VMImage | None = None
    docker_image_ref: str | None = None

    model_config = ConfigDict(extra="forbid")

    _ = model_validator(mode="before")(validators.validate_only_one_must_be_set)


class BaseWorkbenchModel(BaseInstanceModel):
    name: WorkbenchName
    machine_type: str = "e2-standard-2"
    gpu: GPU | None = None
    data_disk: Disk | None = None
    subnet: str | None = None
    tensorboard_ref: str | None = None


class InstanceModel(BaseWorkbenchModel):
    """
    - `type` - [str] (optional) Type of the notebook, instance, for dispatching purposes.
    - `name`- [str] Custom name for this instance
    - `project_id` - [str] (optional) Overrides GCP Project ID from the `gcp_profile` segment
    - `zone` - [str] (optional) Overrides zone from the `gcp_profile` segment
    - `region` - [str] (optional) Overrides region from the `gcp_profile` segment
    - `labels`- [dict[str, str]] (optional) Custom labels to apply to this instance
    - `service_account` - [str] (optional) Overrides service account from the `gcp_profile` segment
    - `network` - [str] (optional) Overrides network from the `gcp_profile` segment
    - `tags`- [dict[str, str]] (optional) Tags to apply to this instance
    - `metadata`- [Optional[dict[str, Any]]] (optional) Custom metadata to apply to this instance
    - `owner` - [str] This can be either a single user email address and that would be the only one
      able to access the notebook. Or service account and then everyone who has the iam.serviceAccounts.actAs
      permission on the specified service account will be able to connect.
    - `machine_type` - [str] (optional) GCP Compute Engine machine type
    - `gpu`- [GPU] (optional) The hardware GPU accelerator used on this instance.
    - `data_disk` - [Disk] (optional) Data disk configuration to attach to this instance.
    - `kernels` - [list[str]] (optional) Custom kernels given as links to container registry
    - `tensorboard_ref` - [str] (optional) Reference to Vertex Experimetes
    - `subnet`- [str] (optional) Subnetwork of a given network
    - `internal_ip_only` - [bool] (optional) Public or private (default) IP address
    - `idle_shutdown_timeout` - [int] (optional) Time in minutes, between 10 and 1440, defaults to 720. If None,
        there is no idle shutdown
    - `post_startup_script` - [str] (optional) Path to a script that will be executed after the instance is started.
    - `post_startup_script_behavior` - [str] Defines the behavior of the post startup script.
        Documentation https://cloud.google.com/vertex-ai/docs/workbench/instances/manage-metadata
    - `environment_auto_upgrade` - [str] (optional) Cron schedule for environment auto-upgrade.
    - `delete_to_trash` - [bool] (optional) If true, the instance will be deleted to trash.
    - `report_health` - [bool] (optional) If true, the instance will report health to Cloud Monitoring
    """

    type: Literal["instance"] = "instance"
    zone: str
    owner: EmailStr | None = None
    boot_disk: Disk | None = None
    environment: NotebookEnvironment = NotebookEnvironment(vm_image=VMImage())
    no_public_ip: bool = True
    enable_dataproc: bool = False
    enable_ip_forwarding: bool = False
    no_proxy_access: bool = False
    enable_monitoring: bool = True
    idle_shutdown_timeout: int | None = Field(ge=10, le=1440, default=720)  # 12 hours
    collaborative: bool = False
    env_vars: dict[str, str] | None = None
    bucket_mounts: list[BucketMount] | None = None
    post_startup_script: str | None = None  # todo: add validation for existing object in bucket
    post_startup_script_behavior: Literal[
        "run_once", "run_every_start", "download_and_run_every_start"
    ] = "run_once"
    environment_auto_upgrade: str | None = None
    delete_to_trash: bool = False
    report_health: bool = True

    _environment_auto_upgrade = field_validator("environment_auto_upgrade")(
        validators.validate_cron_schedule
    )
    _machine_type = field_validator("machine_type")(validators.validate_machine_type)
