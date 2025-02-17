import unittest

import pytest
from pydantic.error_wrappers import ValidationError

from wanna.core.models.training_custom_job import (
    TrainingCustomJobModel,
    WorkerPoolModel,
)


class TestWorkerPoolSpecModel(unittest.TestCase):
    def test_worker_pool_only_python_is_enough(self):
        WorkerPoolModel.model_validate(
            {
                "python_package": {
                    "docker_image_ref": "a",
                    "package_gcs_uri": "a",
                    "module_name": "c",
                }
            }
        )

    def test_worker_pool_only_container_is_enough(self):
        WorkerPoolModel.model_validate({"container": {"docker_image_ref": "a"}})

    def test_worker_pool_container_or_python_must_be_set(self):
        with pytest.raises(ValidationError):
            WorkerPoolModel.model_validate({"machine_type": "n1-standard-4"})

    def test_worker_pool_not_both_container_or_python_can_be_set(self):
        with pytest.raises(ValidationError):
            WorkerPoolModel.model_validate(
                {
                    "python_package": {
                        "docker_image_ref": "a",
                        "package_gcs_uri": "a",
                        "module_name": "c",
                    },
                    "container_spec": {"docker_image_ref": "a"},
                }
            )


class TestTrainingCustomJobModel(unittest.TestCase):
    def test_base_output_directory_default(self):
        model = TrainingCustomJobModel.model_validate(
            {
                "name": "a",
                "region": "europe-west4",
                "bucket": "my-bucket",
                "project_id": "gcp-project",
                "worker": {"container": {"docker_image_ref": "a"}},
            }
        )
        assert model.base_output_directory == "gs://my-bucket/wanna-jobs/a/outputs"
