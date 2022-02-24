from wanna.cli.plugins.notebook.models import (
    Network,
    NotebookEnvironment,
    NotebookDisk,
    NotebookGPU,
    NotebookModel,
)
from pydantic.error_wrappers import ValidationError
from tests.mocks import mocks
import pytest


def test_notebook_environment_only_container_is_set(mocker):
    mocker.patch(
        "wanna.cli.utils.gcp.gcp.ImagesClient",
        mocks.MockImagesClient,
    )
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


def test_notebook_environment_container_and_vm_image_is_set(mocker):
    mocker.patch(
        "wanna.cli.utils.gcp.gcp.ImagesClient",
        mocks.MockImagesClient,
    )
    with pytest.raises(ValidationError) as e_info:
        model = NotebookEnvironment.parse_obj(
            {
                "container_image": "docker.org/my-image",
                "vm_image": {"framework": "tf", "version": "ent-2-3-cu110"},
            }
        )


def test_notebook_network_short_name():
    network_id = "network-x"
    try:
        model = Network.parse_obj({"network_id": network_id})
    except ValidationError:
        assert False, f"network_id {network_id} raised an exception during validation"


def test_notebook_network_full_name():
    network_id = "projects/gcp-project/global/networks/network-x"
    try:
        model = Network.parse_obj({"network_id": network_id})
    except ValidationError:
        assert False, f"network_id {network_id} raised an exception during validation"


def test_notebook_disk_valid_type():
    disk_type = "pd_ssd"
    try:
        model = NotebookDisk.parse_obj({"disk_type": disk_type, "size_gb": 500})
    except ValidationError:
        assert False, f"Disk type {disk_type} raised an exception during validation"


def test_notebook_gpu_type_invalid():
    gpu_type = "super_tesla"
    with pytest.raises(ValidationError) as e_info:
        model = NotebookGPU.parse_obj({"count": 1, "accelerator_type": gpu_type})


def test_notebook_invalid_machine_type(mocker):
    machine_type = "dobry-stroj-chcu"
    mocker.patch(
        "wanna.cli.utils.gcp.gcp.ZonesClient",
        mocks.MockZonesClient,
    )
    mocker.patch(
        "wanna.cli.utils.gcp.gcp.MachineTypesClient",
        mocks.MockMachineTypesClient,
    )
    with pytest.raises(ValidationError) as e_info:
        model = NotebookModel.parse_obj(
        {
            "name": "my-notebook",
            "project_id": "gcp-project",
            "zone": "europe-west4-a",
            "machine_type": machine_type,
        }
    )
