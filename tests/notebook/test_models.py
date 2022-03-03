import pytest
from mock import patch
from pydantic.error_wrappers import ValidationError
from wanna.cli.models.notebook import (
    Network,
    NotebookEnvironment,
    NotebookDisk,
    NotebookGPU,
    NotebookModel,
)

from tests.mocks import mocks


@patch(
    "wanna.cli.utils.gcp.gcp.MachineTypesClient",
    mocks.MockMachineTypesClient,
)
@patch(
    "wanna.cli.utils.gcp.gcp.ImagesClient",
    mocks.MockImagesClient,
)
@patch(
    "wanna.cli.utils.gcp.gcp.ZonesClient",
    mocks.MockZonesClient,
)
class TestNotebookModel:
    def setup(self):
        ...

    def test_notebook_environment_only_container_is_set(self):
        try:
            model = NotebookEnvironment.parse_obj(
                {
                    "container_image": "docker.org/my-image",
                }
            )
        except ValidationError:
            assert (
                False
            ), f"Specifying the container image must be enough for notebook environment"

    def test_notebook_environment_container_and_vm_image_is_set(self):
        with pytest.raises(ValidationError) as e_info:
            model = NotebookEnvironment.parse_obj(
                {
                    "container_image": "docker.org/my-image",
                    "vm_image": {"framework": "tf", "version": "ent-2-3-cu110"},
                }
            )

    def test_notebook_environment_vm_image(self):
        model = NotebookEnvironment.parse_obj(
            {
                "vm_image": {"framework": "tf", "version": "ent-2-3-cu110"},
            }
        )
        assert model.vm_image.framework == "tf"
        assert model.vm_image.version == "ent-2-3-cu110"

    def test_notebook_network_short_name(self):
        network_id = "network-x"
        try:
            model = Network.parse_obj({"network_id": network_id})
        except ValidationError:
            assert (
                False
            ), f"network_id {network_id} raised an exception during validation"

    def test_notebook_network_full_name(self):
        network_id = "projects/gcp-project/global/networks/network-x"
        try:
            model = Network.parse_obj({"network_id": network_id})
        except ValidationError:
            assert (
                False
            ), f"network_id {network_id} raised an exception during validation"

    def test_notebook_disk_valid_type(self):
        disk_type = "pd_ssd"
        try:
            model = NotebookDisk.parse_obj({"disk_type": disk_type, "size_gb": 500})
        except ValidationError:
            assert False, f"Disk type {disk_type} raised an exception during validation"

    def test_notebook_gpu_type_invalid(self):
        gpu_type = "super_tesla"
        with pytest.raises(ValidationError) as e_info:
            model = NotebookGPU.parse_obj({"count": 1, "accelerator_type": gpu_type})

    def test_notebook_invalid_machine_type(self):
        machine_type = "expelliarmus"
        with pytest.raises(ValidationError) as e_info:
            model = NotebookModel.parse_obj(
                {
                    "name": "my-notebook",
                    "project_id": "gcp-project",
                    "zone": "europe-west4-a",
                    "machine_type": machine_type,
                }
            )
