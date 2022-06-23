import unittest
from pathlib import Path

from google.cloud.notebooks_v1.types import Instance
from mock import patch
from mock.mock import MagicMock

from tests.mocks import mocks
from wanna.core.models.gcp_components import GPU, Disk
from wanna.core.models.notebook import NotebookModel
from wanna.core.services.notebook import NotebookService
from wanna.core.utils.config_loader import load_config_from_yaml


@patch(
    "wanna.core.services.notebook.NotebookServiceClient",
    mocks.MockNotebookServiceClient,
)
class TestNotebookService(unittest.TestCase):
    project_id = "gcp-project"
    zone = "us-east1-a"

    def test_list_running_instances(self):
        config = load_config_from_yaml("samples/notebook/custom_container/wanna.yaml", "default")
        nb_service = NotebookService(config=config, workdir=Path("."))
        running_notebooks = nb_service._list_running_instances(project_id=self.project_id, location=self.zone)
        assert f"projects/{self.project_id}/locations/{self.zone}/instances/nb1" in running_notebooks
        assert f"projects/{self.project_id}/locations/{self.zone}/instances/tf-gpu" in running_notebooks
        assert f"projects/{self.project_id}/locations/{self.zone}/instances/pytorch-notebook" in running_notebooks
        assert f"projects/{self.project_id}/locations/{self.zone}/instances/sectumsempra" not in running_notebooks

    def test_instance_exists(self):
        config = load_config_from_yaml("samples/notebook/custom_container/wanna.yaml", "default")
        nb_service = NotebookService(config=config, workdir=Path("."))
        should_exist = nb_service._instance_exists(
            instance=NotebookModel.parse_obj({"project_id": self.project_id, "zone": self.zone, "name": "tf-gpu"})
        )
        assert should_exist
        should_not_exist = nb_service._instance_exists(
            instance=NotebookModel.parse_obj({"project_id": self.project_id, "zone": self.zone, "name": "confundo"})
        )
        assert not should_not_exist

    def test_validate_jupyterlab_state(self):
        config = load_config_from_yaml("samples/notebook/custom_container/wanna.yaml", "default")
        nb_service = NotebookService(config=config, workdir=Path("."))
        state_1 = nb_service._validate_jupyterlab_state(
            instance_id=f"projects/{self.project_id}/locations/{self.zone}/instances/nb1",
            state=Instance.State.ACTIVE,
        )
        assert state_1
        state_1 = nb_service._validate_jupyterlab_state(
            instance_id=f"projects/{self.project_id}/locations/{self.zone}/instances/tf-gpu",
            state=Instance.State.DELETED,
        )
        assert not state_1

    def test_create_instance_request_network_short_name(self):
        config = load_config_from_yaml("samples/notebook/vm_image/wanna.yaml", "default")
        nb_service = NotebookService(config=config, workdir=Path("."))
        instance = config.notebooks[0]
        instance.network = "little-hangleton"
        request = nb_service._create_instance_request(instance)
        assert request.instance.network == f"projects/{config.gcp_profile.project_id}/global/networks/little-hangleton"

    def test_create_instance_request_network_subnet(self):
        config = load_config_from_yaml("samples/notebook/vm_image/wanna.yaml", "default")
        nb_service = NotebookService(config=config, workdir=Path("."))
        instance = config.notebooks[0]
        instance.network = "little-hangleton"
        instance.subnet = "the-riddle-house"
        request = nb_service._create_instance_request(instance)
        assert (
            request.instance.subnet
            == f"projects/{config.gcp_profile.project_id}/region/{config.gcp_profile.zone}/subnetworks/the-riddle-house"
        )

    def test_create_instance_request_gpu_config(self):
        config = load_config_from_yaml("samples/notebook/vm_image/wanna.yaml", "default")
        nb_service = NotebookService(config=config, workdir=Path("."))
        instance = config.notebooks[0]
        instance.gpu = GPU.parse_obj({"accelerator_type": "NVIDIA_TESLA_V100", "count": 4})
        request = nb_service._create_instance_request(instance)
        assert request.instance.accelerator_config.type_.name == "NVIDIA_TESLA_V100"
        assert request.instance.accelerator_config.core_count == 4

    def test_create_instance_request_custom_container(self):
        config = load_config_from_yaml("samples/notebook/custom_container/wanna.yaml", "default")
        nb_service = NotebookService(config=config, workdir=Path("."))
        instance = config.notebooks[0]
        nb_service.docker_service._build_image = MagicMock(return_value=(None, None, None))
        nb_service.docker_service._pull_image = MagicMock(return_value=None)
        request = nb_service._create_instance_request(instance)
        assert (
            request.instance.container_image.repository
            == "europe-west1-docker.pkg.dev/your-gcp-project-id/wanna-samples/"
            "wanna-notebook-sample-custom-container/custom-notebook-container"
        )
        assert request.instance.container_image.tag == "dev"

    def test_create_instance_request_vm_image(self):
        config = load_config_from_yaml("samples/notebook/vm_image/wanna.yaml", "default")
        nb_service = NotebookService(config=config, workdir=Path("."))
        instance = config.notebooks[0]
        request = nb_service._create_instance_request(instance)
        assert request.instance.vm_image.image_family == "pytorch-1-9-xla-notebooks-debian-10"

    def test_create_instance_request_boot_disk(self):
        config = load_config_from_yaml("samples/notebook/vm_image/wanna.yaml", "default")
        nb_service = NotebookService(config=config, workdir=Path("."))
        instance = config.notebooks[0]
        instance.boot_disk = Disk.parse_obj({"disk_type": "pd_ssd", "size_gb": 500})
        request = nb_service._create_instance_request(instance)
        assert request.instance.boot_disk_type == Instance.DiskType.PD_SSD
        assert request.instance.boot_disk_size_gb == 500

    def test_create_instance_request_data_disk(self):
        config = load_config_from_yaml("samples/notebook/vm_image/wanna.yaml", "default")
        nb_service = NotebookService(config=config, workdir=Path("."))
        instance = config.notebooks[0]
        instance.data_disk = Disk.parse_obj({"disk_type": "pd_balanced", "size_gb": 750})
        request = nb_service._create_instance_request(instance)
        assert request.instance.data_disk_type == Instance.DiskType.PD_BALANCED
        assert request.instance.data_disk_size_gb == 750

    def test_prepare_startup_script(self):
        config = load_config_from_yaml("samples/notebook/julia/wanna.yaml", "default")
        # to allow the test execution even without local docker daemon running
        # which is not needed in this test
        config.docker.cloud_build = True
        nb_service = NotebookService(config=config, workdir=Path("."))
        instance = config.notebooks[0]
        startup_script = nb_service._prepare_startup_script(instance)
        assert (
            "gcsfuse --implicit-dirs --only-dir=data your-staging-bucket-name /home/jupyter/mounted/gcs"
            in startup_script
        )

    def test_build(self):
        config = load_config_from_yaml("samples/notebook/vm_image/wanna.yaml", "default")
        nb_service = NotebookService(config=config, workdir=Path("."))
        assert nb_service.build() == 0
