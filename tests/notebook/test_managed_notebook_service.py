import unittest
from pathlib import Path

from google.cloud.notebooks_v1.types import Runtime
from mock import patch

from tests.mocks import mocks
from wanna.core.models.notebook import ManagedNotebookModel
from wanna.core.services.notebook import ManagedNotebookService
from wanna.core.utils.config_loader import load_config_from_yaml


@patch("wanna.core.services.notebook.ManagedNotebookServiceClient", mocks.MockManagedNotebookServiceClient)
class TestManagedNotebookService(unittest.TestCase):
    project_id = "your-gcp-project-id"
    region = "europe-west1"
    zone = "europe-west1-b"

    def test_list_running_instances(self):
        config = load_config_from_yaml("samples/notebook/managed-notebook/wanna.yaml", "default")
        nb_service = ManagedNotebookService(config=config, workdir=Path("."))
        running_notebooks = nb_service._list_running_instances(project_id=self.project_id, location=self.region)
        assert f"projects/{self.project_id}/locations/{self.region}/runtimes/minimum-setup" in running_notebooks
        assert f"projects/{self.project_id}/locations/{self.region}/runtimes/maximum-setup" in running_notebooks
        assert f"projects/{self.project_id}/locations/{self.region}/runtimes/xyz" not in running_notebooks

    def test_instance_exists(self):
        config = load_config_from_yaml("samples/notebook/managed-notebook/wanna.yaml", "default")
        nb_service = ManagedNotebookService(config=config, workdir=Path("."))
        should_exist = nb_service._instance_exists(
            instance=ManagedNotebookModel.parse_obj(
                {
                    "project_id": self.project_id,
                    "region": self.region,
                    "name": "minimum-setup",
                    "owner": "jacek.hebda@avast.com",
                }
            )
        )
        assert should_exist
        should_not_exist = nb_service._instance_exists(
            instance=ManagedNotebookModel.parse_obj(
                {"project_id": self.project_id, "region": self.region, "name": "xyz", "owner": "jacek.hebda@avast.com"}
            )
        )
        assert not should_not_exist

    def test_validate_jupyterlab_state(self):
        config = load_config_from_yaml("samples/notebook/managed-notebook/wanna.yaml", "default")
        nb_service = ManagedNotebookService(config=config, workdir=Path("."))
        state_1 = nb_service._validate_jupyterlab_state(
            instance_id=f"projects/{self.project_id}/locations/{self.region}/runtimes/minimum-setup",
            state=Runtime.State.ACTIVE,
        )
        assert state_1
        state_2 = nb_service._validate_jupyterlab_state(
            instance_id=f"projects/{self.project_id}/locations/{self.region}/runtimes/maximum-setup",
            state=Runtime.State.STOPPED,
        )
        assert state_2

    def test_build(self):
        config = load_config_from_yaml("samples/notebook/managed-notebook/wanna.yaml", "default")
        nb_service = ManagedNotebookService(config=config, workdir=Path("."))
        assert nb_service.build() == 0

    def test_sync(self):
        config = load_config_from_yaml("samples/notebook/managed-notebook/wanna.yaml", "default")
        nb_service = ManagedNotebookService(config=config, workdir=Path("."))
        self.assertIsNone(nb_service.sync(force=True))

    def test_return_diff_should_delete(self):
        config = load_config_from_yaml("samples/notebook/managed-notebook/wanna.yaml", "default")
        existing_notebook = config.managed_notebooks[1]
        existing_notebook.zone = self.zone
        config.managed_notebooks = [existing_notebook]

        nb_service = ManagedNotebookService(config=config, workdir=Path("."))

        assert nb_service._return_diff() == (
            ["projects/your-gcp-project-id/locations/europe-west1/runtimes/minimum-setup"],
            [],
        )

    def test_return_diff_should_create(self):
        config = load_config_from_yaml("samples/notebook/managed-notebook/wanna.yaml", "default")

        expected_to_be_created = ManagedNotebookModel.parse_obj(
            {
                "name": "jacek-notebook",
                "project_id": self.project_id,
                "owner": "jacek.hebda@avast.com",
                "kernels": ["gcr.io/projectId/imageName1", "gcr.io/projectId/imageName2"],
            }
        )
        config.managed_notebooks.append(expected_to_be_created)

        nb_service = ManagedNotebookService(config=config, workdir=Path("."))
        assert nb_service._return_diff() == ([], [expected_to_be_created])
