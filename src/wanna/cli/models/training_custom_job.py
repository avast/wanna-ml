from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Extra, Field, root_validator

from wanna.cli.models.base_instance import BaseInstanceModel


class JobGPUModel(BaseModel, extra=Extra.forbid):
    count: Literal[1, 2, 4, 8] = 1
    accelerator_type: str


class PythonPackageSpecModel(BaseModel, extra=Extra.forbid):
    executor_image_uri: str
    package_uris: List[str]
    python_module: str
    args: Optional[List[str]]
    env: Optional[List[Dict[str, str]]]


class ContainerSpecModel(BaseModel, extra=Extra.forbid):
    image_uri: str
    command: Optional[List[str]]
    args: Optional[List[str]]
    env: Optional[List[Dict[str, str]]]


class WorkerPoolSpecModel(BaseModel, extra=Extra.forbid):
    python_package_spec: Optional[PythonPackageSpecModel]
    container_spec: Optional[ContainerSpecModel]
    machine_type: str = "n1-standard-4"
    gpu: Optional[JobGPUModel]
    boot_disk_type: Literal["pd-ssd", "pd-standard"] = "pd-ssd"
    boot_disk_size_gb: int = Field(ge=100, le=65535, default=100)
    replica_count: int = 1

    @root_validator
    def one_from_python_or_container_spec_must_be_set(cls, values):  # pylint: disable=no-self-argument,no-self-use
        if values.get("python_package_spec") and values.get("container_spec"):
            raise ValueError("Only one of python_package_spec or container_spec can be set")
        if not values.get("python_package_spec") and not values.get("container_spec"):
            raise ValueError("At least one of python_package_spec or container_spec must be set")
        return values


class WorkerPoolSpecsModel(BaseModel, extra=Extra.forbid):
    master: WorkerPoolSpecModel
    worker: Optional[WorkerPoolSpecModel]
    reduction_server: Optional[WorkerPoolSpecModel]
    evaluator: Optional[WorkerPoolSpecModel]


class TrainingCustomJobModel(BaseInstanceModel):
    name: str
    region: str
    timeout_seconds: int = 60 * 60 * 24  # 24 hours
    worker_pool_specs: WorkerPoolSpecsModel
    enable_web_access: bool = False
    network: Optional[str]
    bucket: str
    base_output_directory: Optional[str]

    @root_validator(pre=False)
    def _set_base_output_directory_if_not_provided(  # pylint: disable=no-self-argument,no-self-use
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not values.get("base_output_directory"):
            values["base_output_directory"] = f"/jobs/{values.get('name')}/outputs"
        return values
