import sys
from typing import Any, Dict, List, Optional, Union

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

from pydantic import BaseModel, Extra, Field, root_validator, validator
from typing_extensions import Annotated

from wanna.core.models.base_instance import BaseInstanceModel
from wanna.core.models.gcp_components import GPU, Disk


class PythonPackageModel(BaseModel, extra=Extra.forbid):
    docker_image_ref: str
    package_gcs_uri: str
    module_name: str


class ContainerModel(BaseModel, extra=Extra.forbid):
    docker_image_ref: str
    command: Optional[List[str]]


class WorkerPoolModel(BaseModel, extra=Extra.forbid):
    python_package: Optional[PythonPackageModel]
    container: Optional[ContainerModel]
    args: Optional[List[Union[str, float, int]]]
    env: Optional[Dict[str, str]]
    machine_type: str = "n1-standard-4"
    gpu: Optional[GPU]
    boot_disk: Optional[Disk]
    replica_count: int = 1

    # _machine_type = validator("machine_type", allow_reuse=True)(validators.validate_machine_type)

    @root_validator
    def one_from_python_or_container_spec_must_be_set(
        cls, values
    ):  # pylint: disable=no-self-argument,no-self-use
        if values.get("python_package") and values.get("container"):
            raise ValueError("Only one of python_package or container can be set")
        if not values.get("python_package") and not values.get("container"):
            raise ValueError("At least one of python_package or container must be set")
        return values


class ReductionServerModel(BaseModel, extra=Extra.forbid):
    replica_count: int
    machine_type: str
    container_uri: str


class IntegerParameter(BaseModel, extra=Extra.forbid):
    type: Literal["integer"]
    var_name: str
    min: int
    max: int
    scale: Literal["log", "linear"] = "linear"


class DoubleParameter(BaseModel, extra=Extra.forbid):
    type: Literal["double"]
    var_name: str
    min: float
    max: float
    scale: Literal["log", "linear"] = "linear"


class CategoricalParameter(BaseModel, extra=Extra.forbid):
    type: Literal["categorical"]
    var_name: str
    values: List[str]


class DiscreteParameter(BaseModel, extra=Extra.forbid):
    type: Literal["discrete"]
    var_name: str
    scale: Literal["log", "linear"] = "linear"
    values: List[int]


HyperParamater = Annotated[
    Union[IntegerParameter, DoubleParameter, CategoricalParameter, DiscreteParameter],
    Field(discriminator="type"),
]


class HyperparameterTuning(BaseModel):
    """
    - `metrics` - Dictionary of type [str, Literal["minimize", "maximize"]]
    - `parameters` - List[HyperParamater] defined per var_name, type, min, max, scale
    - `max_trial_count` - [int] defaults to 15
    - `parallel_trial_count` - [int] defaults to 3
    - `search_algorithm` - [str] (optional) Can be "grid" or "random"
    - `encryption_spec` - [str] (optional) The Cloud KMS resource identifier. Has the form:
    projects/my-project/locations/my-region/keyRings/my-kr/cryptoKeys/my-key
    The key needs to be in the same region as where the compute resource is created
    """

    metrics: Dict[str, Literal["minimize", "maximize"]]
    parameters: List[HyperParamater]
    max_trial_count: int = 15
    parallel_trial_count: int = 3
    search_algorithm: Optional[Literal["grid", "random"]]
    encryption_spec: Optional[str]


class BaseCustomJobModel(BaseInstanceModel):
    """
    - `name` - [str] Custom name for this instance
    - `project_id' - [str] (optional) Overrides GCP Project ID from the `gcp_profile` segment
    - `zone` - [str] (optional) Overrides zone from the `gcp_profile` segment
    - `region` - [str] (optional) Overrides region from the `gcp_profile` segment
    - `labels`- [Dict[str, str]] (optional) Custom labels to apply to this instance
    - `service_account` - [str] (optional) Overrides service account from the `gcp_profile` segment
    - `network` - [str] (optional) Overrides network from the `gcp_profile` segment
    - `tags`- [Dict[str, str]] (optional) Tags to apply to this instance
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
    - `env_vars` - Dict[str, str] (optional) Environment variables to be propagated to the job
    """

    region: str
    enable_web_access: bool = False
    bucket: str
    base_output_directory: Optional[str]
    tensorboard_ref: Optional[str]
    timeout_seconds: int = 60 * 60 * 24  # 24 hours
    encryption_spec: Optional[Any]
    env_vars: Optional[Dict[str, str]]

    @root_validator(pre=False)
    def _set_base_output_directory_if_not_provided(  # pylint: disable=no-self-argument,no-self-use
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not values.get("base_output_directory"):
            values[
                "base_output_directory"
            ] = f"gs://{values.get('bucket')}/wanna-jobs/{values.get('name')}/outputs"
        return values

    @root_validator(pre=False)
    def _service_account_must_be_set_when_using_tensorboard(  # pylint: disable=no-self-argument,no-self-use
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        if values.get("tensorboard_ref") and not values.get("service_account"):
            raise ValueError(
                "service_account must be set when using tensorboard in jobs"
            )
        return values


# https://cloud.google.com/vertex-ai/docs/training/create-custom-job
class CustomJobModel(BaseCustomJobModel):
    workers: List[WorkerPoolModel]
    hp_tuning: Optional[HyperparameterTuning]

    @validator("workers", pre=False)
    def _worker_pool_must_have_same_spec(  # pylint: disable=no-self-argument,no-self-use
        cls, workers: List[WorkerPoolModel]
    ) -> List[WorkerPoolModel]:
        if workers:
            python_packages = list(
                filter(lambda w: w.python_package is not None, workers)
            )
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
    reduction_server: Optional[ReductionServerModel]


JobModelTypeAlias = Union[CustomJobModel, TrainingCustomJobModel]
