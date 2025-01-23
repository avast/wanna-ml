from pathlib import Path

import pytest
from google.cloud.notebooks_v2 import DiskType, State
from google.cloud.notebooks_v2.types import Instance
from mock import patch
from mock.mock import MagicMock

from tests.mocks import mocks
from wanna.core.models.gcp_components import GPU, Disk
from wanna.core.models.workbench import InstanceModel
from wanna.core.services.workbench_instance import WorkbenchInstanceService
from wanna.core.utils.config_loader import load_config_from_yaml


@pytest.fixture
def custom_container_config():
    return load_config_from_yaml(
        Path("samples") / "samples" / "notebook" / "custom_container" / "wanna.yaml", "default"
    )


@pytest.fixture
def vm_image_config():
    return load_config_from_yaml(Path("samples") / "notebook" / "vm_image" / "wanna.yaml", "default")


@patch(
    "wanna.core.services.workbench_instance.NotebookServiceClient",
    mocks.MockWorkbenchInstanceServiceClient,
)
class TestWorkbenchInstanceService:
    project_id = "gcp-project"
    zone = "us-east1-a"

    def test_list_running_instances(self, custom_container_config):
        config = custom_container_config
        nb_service = WorkbenchInstanceService(config=config, workdir=Path("."))
        running_notebooks = nb_service._list_running_instances(project_id=self.project_id, location=self.zone)
        assert f"projects/{self.project_id}/locations/{self.zone}/instances/nb1" in running_notebooks
        assert f"projects/{self.project_id}/locations/{self.zone}/instances/tf-gpu" in running_notebooks
        assert f"projects/{self.project_id}/locations/{self.zone}/instances/pytorch-notebook" in running_notebooks
        assert f"projects/{self.project_id}/locations/{self.zone}/instances/sectumsempra" not in running_notebooks

    def test_instance_exists(self, custom_container_config):
        config = custom_container_config
        nb_service = WorkbenchInstanceService(config=config, workdir=Path("."))
        should_exist = nb_service._instance_exists(
            instance=InstanceModel.parse_obj({"project_id": self.project_id, "zone": self.zone, "name": "tf-gpu"})
        )
        assert should_exist
        should_not_exist = nb_service._instance_exists(
            instance=InstanceModel.parse_obj({"project_id": self.project_id, "zone": self.zone, "name": "confundo"})
        )
        assert not should_not_exist

    def test_validate_jupyterlab_state(self, custom_container_config):
        config = custom_container_config
        nb_service = WorkbenchInstanceService(config=config, workdir=Path("."))
        state_1 = nb_service._validate_jupyterlab_state(
            instance_id=f"projects/{self.project_id}/locations/{self.zone}/instances/nb1",
            state=State.ACTIVE,
        )
        assert state_1
        state_1 = nb_service._validate_jupyterlab_state(
            instance_id=f"projects/{self.project_id}/locations/{self.zone}/instances/tf-gpu",
            state=State.DELETED,
        )
        assert not state_1

    def test_create_instance_request_network_short_name(self, vm_image_config):
        config = vm_image_config
        nb_service = WorkbenchInstanceService(config=config, workdir=Path("."))
        instance = config.workbench_instances[0]
        instance.network = "little-hangleton"
        instance.subnet = "the-riddle-house"
        request = nb_service._create_instance_request(instance)
        assert (
            request.instance.gce_setup.network_interfaces[0].network
            == "projects/123456789/global/networks/little-hangleton"
        )

    def test_create_instance_request_network_subnet(self, vm_image_config):
        config = vm_image_config
        nb_service = WorkbenchInstanceService(config=config, workdir=Path("."))
        instance = config.workbench_instances[0]
        instance.network = "little-hangleton"
        instance.subnet = "the-riddle-house"
        request = nb_service._create_instance_request(instance)
        assert (
            request.instance.gce_setup.network_interfaces[0].subnet
            == f"projects/123456789/regions/{config.gcp_profile.region}/subnetworks/the-riddle-house"
        )

    def test_create_instance_request_gpu_config(self, vm_image_config):
        config = vm_image_config
        nb_service = WorkbenchInstanceService(config=config, workdir=Path("."))
        instance = config.workbench_instances[0]
        instance.gpu = GPU.parse_obj({"accelerator_type": "NVIDIA_TESLA_V100", "count": 4})
        request = nb_service._create_instance_request(instance)
        assert request.instance.gce_setup.accelerator_configs[0].type_.name == "NVIDIA_TESLA_V100"
        assert request.instance.gce_setup.accelerator_configs[0].core_count == 4

    def test_create_instance_request_custom_container(self, custom_container_config):
        config = custom_container_config
        nb_service = WorkbenchInstanceService(config=config, workdir=Path("."))
        instance = config.workbench_instances[0]
        nb_service.docker_service._build_image = MagicMock(return_value=(None, None, None))
        nb_service.docker_service._pull_image = MagicMock(return_value=None)
        request = nb_service._create_instance_request(instance)
        assert (
            request.instance.gce_setup.container_image.repository
            == "europe-west1-docker.pkg.dev/your-gcp-project-id/wanna-samples/"
            "wanna-notebook-sample-custom-container/custom-notebook-container"
        )
        assert request.instance.gce_setup.container_image.tag == "dev"

    def test_create_instance_request_vm_image(self, vm_image_config):
        config = vm_image_config
        nb_service = WorkbenchInstanceService(config=config, workdir=Path("."))
        instance = config.workbench_instances[0]
        request = nb_service._create_instance_request(instance)
        assert request.instance.gce_setup.vm_image.family == "pytorch-1-9-xla-notebooks-debian-10"

    def test_create_instance_request_boot_disk(self, vm_image_config):
        config = vm_image_config
        nb_service = WorkbenchInstanceService(config=config, workdir=Path("."))
        instance = config.workbench_instances[0]
        instance.boot_disk = Disk.parse_obj({"disk_type": "pd_ssd", "size_gb": 500})
        request = nb_service._create_instance_request(instance)
        assert request.instance.gce_setup.boot_disk.disk_type == DiskType.PD_SSD
        assert request.instance.gce_setup.boot_disk.disk_size_gb == 500

    def test_create_instance_request_data_disk(self, vm_image_config):
        config = vm_image_config
        nb_service = WorkbenchInstanceService(config=config, workdir=Path("."))
        instance = config.workbench_instances[0]
        instance.data_disk = Disk.parse_obj({"disk_type": "pd_balanced", "size_gb": 750})
        request = nb_service._create_instance_request(instance)
        assert request.instance.gce_setup.data_disks[0].disk_type == DiskType.PD_BALANCED
        assert request.instance.gce_setup.data_disks[0].disk_size_gb == 750

    def test_prepare_startup_script(self, custom_container_config):
        config = custom_container_config
        # to allow the test execution even without local docker daemon running
        # which is not needed in this test
        config.docker.cloud_build = True
        nb_service = WorkbenchInstanceService(config=config, workdir=Path("."))
        instance = config.workbench_instances[0]
        startup_script = nb_service._prepare_startup_script(instance)
        assert "gcsfuse --implicit-dirs your-staging-bucket-name /gcs/your-staging-bucket-name" in startup_script

    def test_build(self, vm_image_config):
        config = vm_image_config
        nb_service = WorkbenchInstanceService(config=config, workdir=Path("."))
        assert nb_service.build() == 0
