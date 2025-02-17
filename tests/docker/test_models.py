import unittest

from wanna.core.models.docker import DockerModel


class TestDockerModel(unittest.TestCase):
    def test_local_build_image(self):
        DockerModel.model_validate(
            {
                "images": [
                    {
                        "name": "expecto-patronum",
                        "build_type": "local_build_image",
                        "context_dir": "/a/b",
                        "dockerfile": "/a/b/dockerfile",
                    }
                ],
                "repository": "wanna-samples",
            }
        )

    def test_provided_image(self):
        DockerModel.model_validate(
            {
                "images": [
                    {
                        "build_type": "provided_image",
                        "name": "slytherin",
                        "image_url": "eu.gcr.io/expecto/patronum:latest",
                    }
                ],
                "repository": "wanna-samples",
            }
        )

    def test_notebook_ready_image(self):
        DockerModel.model_validate(
            {
                "images": [
                    {
                        "name": "expecto-patronum",
                        "build_type": "notebook_ready_image",
                        "requirements_txt": "/a/b/requirements.txt",
                    }
                ],
                "repository": "wanna-samples",
            }
        )
