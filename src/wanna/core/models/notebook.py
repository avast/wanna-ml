from typing import List, Optional

from pydantic import BaseModel, EmailStr, Extra, Field, root_validator, validator

from wanna.core.models.base_instance import BaseInstanceModel
from wanna.core.models.gcp_components import GPU, Disk, VMImage
from wanna.core.utils import validators


class BucketMount(BaseModel, extra=Extra.forbid):
    bucket_name: str
    mount_path: str = "/gcs"

    _bucket_name = validator("bucket_name")(validators.validate_bucket_name)


class NotebookEnvironment(BaseModel, extra=Extra.forbid):
    vm_image: Optional[VMImage]
    docker_image_ref: Optional[str]

    _ = root_validator()(validators.validate_only_one_must_be_set)


class NotebookModel(BaseInstanceModel):
    """
    - `name`- [str] Custom name for this instance
    - `project_id' - [str] (optional) Overrides GCP Project ID from the `gcp_profile` segment
    - `zone` - [str] (optional) Overrides zone from the `gcp_profile` segment
    - `region` - [str] (optional) Overrides region from the `gcp_profile` segment
    - `labels`- [Dict[str, str]] (optional) Custom labels to apply to this instance
    - `service_account` - [str] (optional) Overrides service account from the `gcp_profile` segment
    - `network` - [str] Overrides network from the `gcp_profile` segment
    - `tags`- [Dict[str, str]] (optional) Tags to apply to this instance
    - `metadata`- [str] (optional) Custom metadata to apply to this instance
    - `machine_type` - [str] (optional) GCP Compute Engine machine type
    - `environment` [NotebookEnvironment] (optional) Notebook Environment defined by a docker image reference
    - `instance_owner` - [str] (optional) Currently supports one owner only. If not specified, all of the service
      account users of your VM instance’s service account can use the instance.
      If specified, only the owner will be able to access the notebook.
    - `gpu`- [GPU] (optional) The hardware GPU accelerator used on this instance.
    - `boot_disk` - [Disk] (optional) Boot disk configuration to attach to this instance.
    - `data_disk` - [Disk] (optional) Data disk configuration to attach to this instance.
    - `bucket_mounts` - [List[BucketMount]] (optional) List of buckets to be accessible from the notebook
    - `subnet`- [str] (optional) Subnetwork of a given network
    - `tensorboard_ref` - [str] (optional) Reference to Vertex Experimetes
    - `no_public_ip` - [bool] (optional) Public or private (default) IP address
    - `no_proxy_access` - [bool] (optional) If true, the notebook instance will not register with the proxy
    """

    name: str = Field(min_length=3, max_length=63, to_lower=True, regex="^[a-z][a-z0-9-]*[a-z0-9]$")
    zone: str
    machine_type: str = "n1-standard-4"
    environment: NotebookEnvironment = NotebookEnvironment(vm_image=VMImage(framework="common", version="cpu"))
    instance_owner: Optional[EmailStr]
    gpu: Optional[GPU]
    boot_disk: Optional[Disk]
    data_disk: Optional[Disk]
    bucket_mounts: Optional[List[BucketMount]]
    network: Optional[str]
    subnet: Optional[str]
    tensorboard_ref: Optional[str]
    enable_monitoring: bool = True
    no_public_ip: bool = True
    no_proxy_access: bool = False

    _machine_type = validator("machine_type")(validators.validate_machine_type)


class ManagedNotebookModel(BaseInstanceModel):
    """
    - `name`- [str] Custom name for this instance
    - `project_id' - [str] (optional) Overrides GCP Project ID from the `gcp_profile` segment
    - `zone` - [str] (optional) Overrides zone from the `gcp_profile` segment
    - `region` - [str] (optional) Overrides region from the `gcp_profile` segment
    - `labels`- [Dict[str, str]] (optional) Custom labels to apply to this instance
    - `service_account` - [str] (optional) Overrides service account from the `gcp_profile` segment
    - `network` - [str] (optional) Overrides network from the `gcp_profile` segment
    - `tags`- [Dict[str, str]] (optional) Tags to apply to this instance
    - `metadata`- [str] (optional) Custom metadata to apply to this instance
    - `owner` - [str] This can be either a single user email address and that would be the only one
      able to access the notebook. Or service account and then everyone who has the iam.serviceAccounts.actAs
      permission on the specified service account will be able to connect.
    - `machine_type` - [str] (optional) GCP Compute Engine machine type
    - `gpu`- [GPU] (optional) The hardware GPU accelerator used on this instance.
    - `data_disk` - [Disk] (optional) Data disk configuration to attach to this instance.
    - `kernels` - [List[str]] (optional) Custom kernels given as links to container registry
    - `tensorboard_ref` - [str] (optional) Reference to Vertex Experimetes
    - `subnet`- [str] (optional) Subnetwork of a given network
    - `internal_ip_only` - [bool] (optional) Public or private (default) IP address
    - `idle_shutdown` - [bool] (optional) Turning off the notebook after the timeout, can be
      true (default) or false
    - `idle_shutdown_timeout` - [int] (optional) Time in minutes, between 10 and 1440, defaults to 180
    """

    name: str = Field(min_length=3, max_length=63, to_lower=True, regex="^[a-z][a-z0-9-]*[a-z0-9]$")
    owner: str
    machine_type: Optional[str] = "n1-standard-4"
    gpu: Optional[GPU]
    data_disk: Optional[Disk]
    kernel_docker_image_refs: Optional[List[str]]
    tensorboard_ref: Optional[str]
    network: Optional[str]
    subnet: Optional[str]
    internal_ip_only: Optional[bool] = True
    idle_shutdown: Optional[bool]
    idle_shutdown_timeout: Optional[int] = Field(ge=10, le=1440)
