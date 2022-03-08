import unittest

from wanna.cli.models.docker import DockerModel


class TestDockerModel(unittest.TestCase):
    def test_local_build_image(self):
        DockerModel.parse_obj(
            {
                "images": [
                    {
                        "name": "expecto-patronum",
                        "build_type": "local_build_image",
                        "context_dir": "/a/b",
                        "dockerfile": "/a/b/dockerfile",
                    }
                ]
            }
        )

    def test_provided_image(self):
        DockerModel.parse_obj(
            {
                "images": [
                    {
                        "build_type": "provided_image",
                        "image_url": "eu.gcr.io/expecto/patronum:latest",
                    }
                ]
            }
        )

    def test_notebook_ready_image(self):
        DockerModel.parse_obj(
            {
                "images": [
                    {
                        "name": "expecto-patronum",
                        "build_type": "notebook_ready_image",
                        "requirements_txt": "/a/b/requirements.txt",
                    }
                ]
            }
        )
