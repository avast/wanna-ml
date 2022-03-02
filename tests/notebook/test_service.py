from wanna.cli.plugins.notebook.service import NotebookService
from google.cloud.notebooks_v1.types import Instance
from tests.mocks import mocks
from wanna.cli.models.notebook import (
    NotebookModel,
    Network,
    NotebookGPU,
    NotebookEnvironment,
    NotebookDisk,
    BucketMount,
)
from mock import patch
import pytest


@patch(
    "wanna.cli.plugins.notebook.service.NotebookServiceClient",
    mocks.MockNotebookServiceClient,
)
@patch(
    "wanna.cli.utils.gcp.gcp.ZonesClient",
    mocks.MockZonesClient,
)
@patch(
    "wanna.cli.utils.gcp.gcp.ImagesClient",
    mocks.MockImagesClient,
)
@patch(
    "wanna.cli.utils.gcp.validators.StorageClient",
    mocks.MockStorageClient,
)
class TestNotebookService:
    def setup(self):
        self.project_id = "gcp-project"
        self.zone = "us-east1-a"

    def test_list_running_instances(self, mocker):
        nb_service = NotebookService()
        running_notebooks = nb_service._list_running_instances(
            project_id=self.project_id, location=self.zone
        )
        assert (
            f"projects/{self.project_id}/locations/{self.zone}/instances/nb1"
            in running_notebooks
        )
        assert (
            f"projects/{self.project_id}/locations/{self.zone}/instances/tf-gpu"
            in running_notebooks
        )
        assert (
            f"projects/{self.project_id}/locations/{self.zone}/instances/pytorch-notebook"
            in running_notebooks
        )
        assert (
            f"projects/{self.project_id}/locations/{self.zone}/instances/sectumsempra"
            not in running_notebooks
        )

    def test_instance_exists(self):
        nb_service = NotebookService()
        should_exist = nb_service._instance_exists(
            instance=NotebookModel.parse_obj(
                {"project_id": self.project_id, "zone": self.zone, "name": "tf-gpu"}
            )
        )
        assert should_exist
        should_not_exist = nb_service._instance_exists(
            instance=NotebookModel.parse_obj(
                {"project_id": self.project_id, "zone": self.zone, "name": "confundo"}
            )
        )
        assert not should_not_exist

    def test_validate_jupyterlab_state(self):
        nb_service = NotebookService()
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
        nb_service = NotebookService()
        instance = get_base_notebook()
        instance.network = Network.parse_obj({"network_id": "little-hangleton"})
        request = nb_service._create_instance_request(instance)
        assert (
            request.instance.network
            == f"projects/{self.project_id}/global/networks/little-hangleton"
        )

    def test_create_instance_request_network_subnet(self):
        nb_service = NotebookService()
        instance = get_base_notebook()
        instance.network = Network.parse_obj(
            {"network_id": "little-hangleton", "subnet": "the-riddle-house"}
        )
        request = nb_service._create_instance_request(instance)
        assert (
            request.instance.subnet
            == f"projects/{self.project_id}/region/{self.zone}/subnetworks/the-riddle-house"
        )

    def test_create_instance_request_gpu_config(self):
        nb_service = NotebookService()
        instance = get_base_notebook()
        instance.gpu = NotebookGPU.parse_obj(
            {"accelerator_type": "NVIDIA_TESLA_V100", "count": 4}
        )
        request = nb_service._create_instance_request(instance)
        assert request.instance.accelerator_config.type_.name == "NVIDIA_TESLA_V100"
        assert request.instance.accelerator_config.core_count == 4

    def test_create_instance_request_custom_container(self):
        nb_service = NotebookService()
        instance = get_base_notebook()
        instance.environment = NotebookEnvironment.parse_obj(
            {"container_image": "eu.gcr.io/lumos:0.15"}
        )
        request = nb_service._create_instance_request(instance)
        assert request.instance.container_image.repository == "eu.gcr.io/lumos"
        assert request.instance.container_image.tag == "0.15"

    def test_create_instance_request_vm_image(self):
        nb_service = NotebookService()
        instance = get_base_notebook()
        instance.environment = NotebookEnvironment.parse_obj(
            {
                "vm_image": {
                    "framework": "tf2",
                    "version": "ent-2-5-cu110",
                    "os": "debian-10",
                }
            }
        )
        request = nb_service._create_instance_request(instance)
        assert (
            request.instance.vm_image.image_family
            == "tf2-ent-2-5-cu110-notebooks-debian-10"
        )

    def test_create_instance_request_boot_disk(self):
        nb_service = NotebookService()
        instance = get_base_notebook()
        instance.boot_disk = NotebookDisk.parse_obj(
            {"disk_type": "pd_ssd", "size_gb": 500}
        )
        request = nb_service._create_instance_request(instance)
        assert request.instance.boot_disk_type == Instance.DiskType.PD_SSD
        assert request.instance.boot_disk_size_gb == 500

    def test_create_instance_request_data_disk(self):
        nb_service = NotebookService()
        instance = get_base_notebook()
        instance.data_disk = NotebookDisk.parse_obj(
            {"disk_type": "pd_balanced", "size_gb": 750}
        )
        request = nb_service._create_instance_request(instance)
        assert request.instance.data_disk_type == Instance.DiskType.PD_BALANCED
        assert request.instance.data_disk_size_gb == 750

    def test_create_instance_instance_owners(self):
        ...

    def test_prepare_startup_script(self):
        nb_service = NotebookService()
        instance = get_base_notebook()
        instance.bucket_mounts = [
            BucketMount.parse_obj(
                {
                    "bucket_name": "grimauld-place",
                    "bucket_dir": "/number-12",
                    "local_path": "/mounts/gcp",
                }
            )
        ]
        startup_script = nb_service._prepare_startup_script(instance)
        assert (
            "gcsfuse --implicit-dirs --only-dir=/number-12 grimauld-place /mounts/gcp"
            in startup_script
        )


def get_base_notebook():
    return NotebookModel.parse_obj(
        {
            "project_id": "gcp-project",
            "zone": "us-east1-a",
            "name": "confundo",
            "instance_owner": "luna.lovegood@avast.com",
        }
    )
