from dataclasses import dataclass, field
from typing import Dict, List, Optional

from serde import deserialize, serialize

from wanna.cli.docker.models import DockerBuild


@deserialize
@serialize
@dataclass
class BaseOutputDirectory:
    output_uri_prefix: str


@deserialize
@serialize
@dataclass
class Scheduling:
    timeout: str = field(default="")
    restart_job_on_worker_restart: bool = field(default=True)


@deserialize
@serialize
@dataclass
class Env:
    name: str
    value: str

    def __init__(self, name: str, value: str) -> None:
        self.name = name
        self.value = value


@deserialize
@serialize
@dataclass
class ContainerSpec:
    image_uri: str
    env: List[Env]
    command: List[str]
    args: List[str]


@deserialize
@serialize
@dataclass
class PythonPackageSpec:
    executor_image_uri: str  # one of https://cloud.google.com/vertex-ai/docs/training/pre-built-containers
    package_uris: List[str]  # max 100 -> gcs path to python packages
    python_module: str
    args: Optional[List[str]] = field(default=list)
    env: Optional[Env] = field(default=None)


@deserialize
@serialize
@dataclass
class DiskSpec:
    boot_disk_size_gb: int
    boot_disk_type: str


@deserialize
@serialize
@dataclass
class MachineSpec:
    machine_type: str


@deserialize
@serialize
@dataclass
class WorkerPoolSpecs:
    machine_spec: MachineSpec
    replica_count: int
    disk_spec: DiskSpec
    container_spec: Optional[ContainerSpec]
    python_package_spec: Optional[PythonPackageSpec]


@deserialize
@serialize
@dataclass
class CustomJobConfig:
    scheduling: Scheduling
    enable_web_access: bool
    base_output_directory: BaseOutputDirectory
    tensorboard: Optional[str] = field(default_factory=list)
    worker_pool_specs: List[WorkerPoolSpecs] = field(default_factory=list)
    service_account: Optional[str] = field(default=None)
    network: Optional[str] = field(default=None)


@deserialize
@serialize
@dataclass
class JobConfig:
    name: str
    docker: DockerBuild
    job: CustomJobConfig
    version: str = field(default=None)
    region: str = field(default=None)
    location: str = field(default=None)
    project_id: Optional[str] = field(default=None)
    labels: Dict[str, str] = field(default_factory=dict)
