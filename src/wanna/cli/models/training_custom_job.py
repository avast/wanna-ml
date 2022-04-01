from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Extra, Field, root_validator, validator

from wanna.cli.models.base_instance import BaseInstanceModel


class JobGPUModel(BaseModel, extra=Extra.forbid):
    count: Literal[1, 2, 4, 8] = 1
    accelerator_type: str


class PythonPackageModel(BaseModel, extra=Extra.forbid):
    executor_image_uri: str
    package_gcs_uri: str
    module_name: str


class ContainerModel(BaseModel, extra=Extra.forbid):
    image_uri: str
    command: Optional[List[str]]


class WorkerPoolModel(BaseModel, extra=Extra.forbid):
    python_package: Optional[PythonPackageModel]
    container: Optional[ContainerModel]
    args: Optional[List[str]]
    env: Optional[List[Dict[str, str]]]
    machine_type: str = "n1-standard-4"
    gpu: Optional[JobGPUModel]
    boot_disk_type: Literal["pd-ssd", "pd-standard"] = "pd-ssd"
    boot_disk_size_gb: int = Field(ge=100, le=65535, default=100)
    replica_count: int = 1

    @root_validator
    def one_from_python_or_container_spec_must_be_set(cls, values):  # pylint: disable=no-self-argument,no-self-use
        if values.get("python_package") and values.get("container"):
            raise ValueError("Only one of python_package or container can be set")
        if not values.get("python_package") and not values.get("container"):
            raise ValueError("At least one of python_package or container must be set")
        return values


class ReductionServerModel(BaseModel, extra=Extra.forbid):
    replica_count: int
    machine_type: str
    container_uri: str


class BaseCustomJobModel(BaseInstanceModel):
    name: str
    region: str
    enable_web_access: bool = False
    network: Optional[str]
    bucket: str
    base_output_directory: Optional[str]
    tensorboard_ref: Optional[str]
    timeout_seconds: int = 60 * 60 * 24  # 24 hours

    @root_validator(pre=False)
    def _set_base_output_directory_if_not_provided(  # pylint: disable=no-self-argument,no-self-use
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not values.get("base_output_directory"):
            values["base_output_directory"] = f"gs://{values.get('bucket')}/jobs/{values.get('name')}/outputs"
        return values

    @root_validator(pre=False)
    def _service_account_must_be_set_when_using_tensorboard(  # pylint: disable=no-self-argument,no-self-use
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        if values.get("tensorboard_ref") and not values.get("service_account"):
            raise ValueError("service_account must be set when using tensorboard in jobs")
        return values


# https://cloud.google.com/vertex-ai/docs/training/create-custom-job
class CustomJobModel(BaseCustomJobModel):
    workers: List[WorkerPoolModel]

    @validator("workers", pre=False)
    def _worker_pool_must_have_same_spec(  # pylint: disable=no-self-argument,no-self-use
        cls, workers: List[WorkerPoolModel]
    ) -> List[WorkerPoolModel]:
        if workers:
            python_packages = list(filter(lambda w: w.python_package is not None, workers))
            containers = list(filter(lambda w: w.container is not None, workers))
            if len(python_packages) > 0 and len(containers) > 0:
                raise ValueError(
                    "CustomJobs must be of the same spec. " "Either just based on python_package or container"
                )

        return workers


# https://cloud.google.com/vertex-ai/docs/training/create-training-pipeline
class TrainingCustomJobModel(BaseCustomJobModel):
    worker: WorkerPoolModel
    reduction_server: Optional[ReductionServerModel]
