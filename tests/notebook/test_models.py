import unittest

import pytest
from pydantic.error_wrappers import ValidationError

from wanna.core.models.gcp_components import GPU, Disk
from wanna.core.models.workbench import InstanceModel, NotebookEnvironment


class TestNotebookModel(unittest.TestCase):
    def test_notebook_environment_only_container_is_set(self):
        try:
            _ = NotebookEnvironment.model_validate(
                {
                    "docker_image_ref": "ravenclaw",
                }
            )
        except ValidationError:
            assert False, "Specifying the container image must be enough for notebook environment"

    def test_notebook_environment_container_and_vm_image_is_set(self):
        with pytest.raises(ValidationError):
            _ = NotebookEnvironment.model_validate(
                {
                    "docker_ref": "some-defined-docker-image",
                    "vm_image": {"version": "v20241224"},
                }
            )

    def test_notebook_environment_vm_image(self):
        model = NotebookEnvironment.model_validate(
            {
                "vm_image": {"version": "v20241224"},
            }
        )
        assert model.vm_image.version == "v20241224"

    def test_notebook_environment_vm_image_default(self):
        model = NotebookEnvironment.model_validate(
            {
                "vm_image": {},
            }
        )
        assert model.vm_image.version is None

    def test_notebook_disk_valid_type(self):
        disk_type = "pd_ssd"
        try:
            _ = Disk.model_validate({"disk_type": disk_type, "size_gb": 500})
        except ValidationError:
            assert False, f"Disk type {disk_type} raised an exception during validation"

    def test_notebook_gpu_type_invalid(self):
        gpu_type = "super_tesla"
        with pytest.raises(ValidationError):
            _ = GPU.model_validate({"count": 1, "accelerator_type": gpu_type})

    def test_notebook_invalid_machine_type(self):
        machine_type = "expelliarmus"
        with pytest.raises(ValidationError):
            _ = InstanceModel.model_validate(
                {
                    "name": "my-notebook",
                    "project_id": "gcp-project",
                    "zone": "europe-west4-a",
                    "machine_type": machine_type,
                }
            )
