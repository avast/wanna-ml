from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wanna.core.models.base_instance import BaseInstanceModel
from wanna.core.models.gcp_components import GPU, Disk


class PythonPackageModel(BaseModel):
    docker_image_ref: str
    package_gcs_uri: str
    module_name: str

    model_config = ConfigDict(extra="forbid")


class ContainerModel(BaseModel):
    docker_image_ref: str
    command: list[str] | None = None

    model_config = ConfigDict(extra="forbid")


class WorkerPoolModel(BaseModel):
    python_package: PythonPackageModel | None = None
    container: ContainerModel | None = None
    args: list[str | float | int] | None = None
    env: dict[str, str] | None = None
    machine_type: str = "n1-standard-4"
    gpu: GPU | None = None
    boot_disk: Disk | None = None
    replica_count: int = 1

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    def one_from_python_or_container_spec_must_be_set(cls, values):  # pylint: disable=no-self-argument,no-self-use
        if values.get("python_package") and values.get("container"):
            raise ValueError("Only one of python_package or container can be set")
        if not values.get("python_package") and not values.get("container"):
            raise ValueError("At least one of python_package or container must be set")
        return values


class ReductionServerModel(BaseModel):
    replica_count: int
    machine_type: str
    container_uri: str


class IntegerParameter(BaseModel):
    type: Literal["integer"]
    var_name: str
    min: int
    max: int
    scale: Literal["log", "linear"] = "linear"

    model_config = ConfigDict(extra="forbid")


class DoubleParameter(BaseModel):
    type: Literal["double"]
    var_name: str
    min: float
    max: float
    scale: Literal["log", "linear"] = "linear"

    model_config = ConfigDict(extra="forbid")


class CategoricalParameter(BaseModel):
    type: Literal["categorical"]
    var_name: str
    values: list[str]

    model_config = ConfigDict(extra="forbid")


class DiscreteParameter(BaseModel):
    type: Literal["discrete"]
    var_name: str
    scale: Literal["log", "linear"] = "linear"
    values: list[int]

    model_config = ConfigDict(extra="forbid")


HyperParamater = Annotated[
    Union[IntegerParameter, DoubleParameter, CategoricalParameter, DiscreteParameter],
    Field(discriminator="type"),
]


class HyperparameterTuning(BaseModel):
    """
    - `metrics` - Dictionary of type [str, Literal["minimize", "maximize"]]
    - `parameters` - list[HyperParamater] defined per var_name, type, min, max, scale
    - `max_trial_count` - [int] defaults to 15
    - `parallel_trial_count` - [int] defaults to 3
    - `search_algorithm` - [str] (optional) Can be "grid" or "random"
    - `encryption_spec` - [str] (optional) The Cloud KMS resource identifier. Has the form:
    projects/my-project/locations/my-region/keyRings/my-kr/cryptoKeys/my-key
    The key needs to be in the same region as where the compute resource is created
    """

    metrics: dict[str, Literal["minimize", "maximize"]]
    parameters: list[HyperParamater]
    max_trial_count: int = 15
    parallel_trial_count: int = 3
    search_algorithm: Literal["grid", "random"] | None = None
    encryption_spec: str | None = None


class BaseCustomJobModel(BaseInstanceModel):
    """
    - `name` - [str] Custom name for this instance
    - `project_id' - [str] (optional) Overrides GCP Project ID from the `gcp_profile` segment
    - `zone` - [str] (optional) Overrides zone from the `gcp_profile` segment
    - `region` - [str] (optional) Overrides region from the `gcp_profile` segment
    - `labels`- [dict[str, str]] (optional) Custom labels to apply to this instance
    - `service_account` - [str] (optional) Overrides service account from the `gcp_profile` segment
    - `network` - [str] (optional) Overrides network from the `gcp_profile` segment
    - `tags`- [dict[str, str]] (optional) Tags to apply to this instance
    - `metadata`- [str] (optional) Custom metadata to apply to this instance
    - `enable_web_access` - [bool] Whether you want Vertex AI to enable interactive shell access
    to training containers. Default is False
    - `bucket` - [str] Overrides bucket from the `gcp_profile` segment
    - `base_output_directory` - [str] (optional) Path to where outputs will be saved
    - `tensorboard_ref` - [str] (optional) Name of the Vertex AI Experiment
    - `timeout_seconds` - [int] Job timeout. Defaults to 60 * 60 * 24 s = 24 hours
    - `encryption_spec`- [str] (optional) The Cloud KMS resource identifier. Has the form:
    projects/my-project/locations/my-region/keyRings/my-kr/cryptoKeys/my-key
    The key needs to be in the same region as where the compute resource is created
    - `env_vars` - dict[str, str] (optional) Environment variables to be propagated to the job
    """

    region: str
    enable_web_access: bool = False
    bucket: str
    base_output_directory: str | None = None
    tensorboard_ref: str | None = None
    timeout_seconds: int = 60 * 60 * 24  # 24 hours
    encryption_spec: Any | None = None
    env_vars: dict[str, str] | None = None

    @model_validator(mode="before")
    def _set_base_output_directory_if_not_provided(  # pylint: disable=no-self-argument,no-self-use
        cls, values: dict[str, Any]
    ) -> dict[str, Any]:
        if not values.get("base_output_directory"):
            values["base_output_directory"] = (
                f"gs://{values.get('bucket')}/wanna-jobs/{values.get('name')}/outputs"
            )
        return values

    @model_validator(mode="before")
    def _service_account_must_be_set_when_using_tensorboard(  # pylint: disable=no-self-argument,no-self-use
        cls, values: dict[str, Any]
    ) -> dict[str, Any]:
        if values.get("tensorboard_ref") and not values.get("service_account"):
            raise ValueError("service_account must be set when using tensorboard in jobs")
        return values


# https://cloud.google.com/vertex-ai/docs/training/create-custom-job
class CustomJobModel(BaseCustomJobModel):
    workers: list[WorkerPoolModel]
    hp_tuning: HyperparameterTuning | None = None

    @field_validator("workers", mode="after")
    def _worker_pool_must_have_same_spec(  # pylint: disable=no-self-argument,no-self-use
        cls, workers: list[WorkerPoolModel]
    ) -> list[WorkerPoolModel]:
        if workers:
            python_packages = list(filter(lambda w: w.python_package is not None, workers))
            containers = list(filter(lambda w: w.container is not None, workers))
            if len(python_packages) > 0 and len(containers) > 0:
                raise ValueError(
                    "CustomJobs must be of the same spec. "
                    "Either just based on python_package or container"
                )

        return workers


# https://cloud.google.com/vertex-ai/docs/training/create-training-pipeline
class TrainingCustomJobModel(BaseCustomJobModel):
    worker: WorkerPoolModel
    reduction_server: ReductionServerModel | None = None


JobModelTypeAlias = Union[CustomJobModel, TrainingCustomJobModel]
