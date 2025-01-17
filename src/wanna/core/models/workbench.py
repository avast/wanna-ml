from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Extra, Field, root_validator, validator

from wanna.core.models.base_instance import BaseInstanceModel
from wanna.core.models.gcp_components import GPU, Disk, VMImage
from wanna.core.utils import validators


class BucketMount(BaseModel, extra=Extra.forbid):
    bucket_name: str
    mount_path: str = "/gcs"

    _bucket_name = validator("bucket_name")(validators.validate_bucket_name)


class NotebookEnvironment(BaseModel, extra=Extra.forbid):
    vm_image: Optional[VMImage] = None
    docker_image_ref: Optional[str] = None

    _ = root_validator()(validators.validate_only_one_must_be_set)


class BaseWorkbenchModel(BaseInstanceModel):
    name: str = Field(min_length=3, max_length=63, to_lower=True, regex="^[a-z][a-z0-9-]*[a-z0-9]$")
    machine_type: str = "e2-standard-2"
    gpu: Optional[GPU]
    data_disk: Optional[Disk]
    subnet: Optional[str]
    tensorboard_ref: Optional[str]


class NotebookModel(BaseWorkbenchModel):
    """
    - `name`- [str] Custom name for this instance
    - `project_id' - [str] (optional) Overrides GCP Project ID from the `gcp_profile` segment
    - `zone` - [str] (optional) Overrides zone from the `gcp_profile` segment
    - `region` - [str] (optional) Overrides region from the `gcp_profile` segment
    - `labels`- [dict[str, str]] (optional) Custom labels to apply to this instance
    - `service_account` - [str] (optional) Overrides service account from the `gcp_profile` segment
    - `network` - [str] Overrides network from the `gcp_profile` segment
    - `tags`- [dict[str, str]] (optional) Tags to apply to this instance
    - `metadata`- [str] (optional) Custom metadata to apply to this instance
    - `machine_type` - [str] (optional) GCP Compute Engine machine type
    - `environment` [NotebookEnvironment] (optional) Notebook Environment defined by a docker image reference
    - `owner` - [str] (optional) Currently supports one owner only. If not specified, all of the service
      account users of your VM instance’s service account can use the instance.
      If specified, only the owner will be able to access the notebook.
    - `gpu`- [GPU] (optional) The hardware GPU accelerator used on this instance.
    - `boot_disk` - [Disk] (optional) Boot disk configuration to attach to this instance.
    - `data_disk` - [Disk] (optional) Data disk configuration to attach to this instance.
    - `bucket_mounts` - [list[BucketMount]] (optional) List of buckets to be accessible from the notebook
    - `subnet`- [str] (optional) Subnetwork of a given network
    - `tensorboard_ref` - [str] (optional) Reference to Vertex Experiments
    - `enable_monitoring` - [bool] (optional) Reports system health and notebook metrics to Cloud Monitoring
    - `collaborative` - [bool] (optional) Enable JupyterLab realtime collaboration
    https://jupyterlab.readthedocs.io/en/stable/user/rtc.html
    - `no_public_ip` - [bool] (optional) Public or private (default) IP address
    - `no_proxy_access` - [bool] (optional) If true, the notebook instance will not register with the proxy
    - `idle_shutdown_timeout` - [int] (optional) Time in minutes, between 10 and 1440. After this time of inactivity,
    notebook will be stopped. If the parameter is not set, we don't do anything.
    - `env_vars` - dict[str, str] (optional) Environment variables to be propagated to the notebook
    - `backup` - [str] (optional) Name of the bucket where a data backup is copied (no 'gs://' needed in the name).
    After creation, any changes (including deletion) made to the data disk contents will be synced to the GCS location
    It’s recommended that you enable object versioning for the selected location so you can restore accidentally
    deleted or overwritten files. To prevent sync conflicts, avoid assigning the same location to multiple instances.
    Works only for non-Docker notebooks!
    """

    zone: str
    owner: Optional[EmailStr]
    environment: NotebookEnvironment = NotebookEnvironment(vm_image=VMImage())
    boot_disk: Optional[Disk]
    bucket_mounts: Optional[list[BucketMount]]
    enable_monitoring: bool = True
    collaborative: bool = False
    no_public_ip: bool = True
    no_proxy_access: bool = False
    idle_shutdown_timeout: Optional[int]
    env_vars: Optional[dict[str, str]]
    backup: Optional[str]

    _machine_type = validator("machine_type")(validators.validate_machine_type)


class ManagedNotebookModel(BaseWorkbenchModel):
    """
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
    - `idle_shutdown` - [bool] (optional) Turning off the notebook after the timeout, can be
      true (default) or false
    - `idle_shutdown_timeout` - [int] (optional) Time in minutes, between 10 and 1440, defaults to 180
    """

    owner: Optional[str]
    kernel_docker_image_refs: Optional[list[str]]
    internal_ip_only: bool = True
    idle_shutdown: bool = True
    idle_shutdown_timeout: int = Field(ge=10, le=1440, default=180)


class InstanceModel(BaseWorkbenchModel):
    """
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
    owner: Optional[EmailStr]
    boot_disk: Optional[Disk]
    environment: NotebookEnvironment = NotebookEnvironment(vm_image=VMImage())
    no_public_ip: bool = True
    enable_dataproc: bool = False
    enable_ip_forwarding: bool = False
    no_proxy_access: bool = False
    enable_monitoring: bool = True
    idle_shutdown_timeout: Optional[int] = Field(ge=10, le=1440, default=720)   # 12 hours
    collaborative: bool = False
    env_vars: Optional[dict[str, str]]
    bucket_mounts: Optional[list[BucketMount]]
    post_startup_script: Optional[str]  # todo: add validation for existing object in bucket
    post_startup_script_behavior: Literal["run_once", "run_every_start", "download_and_run_every_start"] = "run_once"
    environment_auto_upgrade: Optional[str] = None
    delete_to_trash: bool = False
    report_health: bool = True

    _environment_auto_upgrade = validator("environment_auto_upgrade")(validators.validate_cron_schedule)
