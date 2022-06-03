import unittest

import pytest
from mock import patch
from pydantic.error_wrappers import ValidationError

from tests.mocks import mocks
from wanna.cli.models.training_custom_job import TrainingCustomJobModel, WorkerPoolModel


class TestWorkerPoolSpecModel(unittest.TestCase):
    def test_worker_pool_only_python_is_enough(self):
        WorkerPoolModel.parse_obj(
            {
                "python_package": {
                    "docker_image_ref": "a",
                    "package_gcs_uri": "a",
                    "module_name": "c",
                }
            }
        )

    def test_worker_pool_only_container_is_enough(self):
        WorkerPoolModel.parse_obj({"container": {"docker_image_ref": "a"}})

    def test_worker_pool_container_or_python_must_be_set(self):
        with pytest.raises(ValidationError):
            WorkerPoolModel.parse_obj({"machine_type": "n1-standard-4"})

    def test_worker_pool_not_both_container_or_python_can_be_set(self):
        with pytest.raises(ValidationError):
            WorkerPoolModel.parse_obj(
                {
                    "python_package": {
                        "docker_image_ref": "a",
                        "package_gcs_uri": "a",
                        "module_name": "c",
                    },
                    "container_spec": {"docker_image_ref": "a"},
                }
            )


@patch(
    "wanna.cli.utils.gcp.gcp.RegionsClient",
    mocks.MockRegionsClient,
)
@patch("wanna.cli.utils.gcp.validators.get_credentials", mocks.mock_get_credentials)
@patch("wanna.cli.utils.gcp.gcp.get_credentials", mocks.mock_get_credentials)
class TestTrainingCustomJobModel(unittest.TestCase):
    def test_base_output_directory_default(self):
        model = TrainingCustomJobModel.parse_obj(
            {
                "name": "a",
                "region": "europe-west4",
                "bucket": "my-bucket",
                "project_id": "gcp-project",
                "worker": {"container": {"docker_image_ref": "a"}},
            }
        )
        assert model.base_output_directory == "gs://my-bucket/jobs/a/outputs"
