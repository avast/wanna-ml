import os
import pathlib
import unittest

from wanna.components.loader import load_wanna_component


class TestWannaComponentLoader(unittest.TestCase):
    def test_wanna_component_loader(self):
        current_dir = pathlib.Path(__file__).parent.resolve()
        docker_image = "docker.avast.com/some/uri"
        os.environ["PREDICTOR_DOCKER_URI"] = docker_image
        comp = load_wanna_component(current_dir / "test_comp.yaml")
        self.assertEqual(
            comp.__dict__["component_spec"].implementation.container.image, docker_image
        )

        del os.environ["PREDICTOR_DOCKER_URI"]
        comp = load_wanna_component(current_dir / "test_comp.yaml")
        self.assertNotEqual(
            comp.__dict__["component_spec"].implementation.container.image, docker_image
        )
        self.assertEqual(
            comp.__dict__["component_spec"].implementation.container.image,
            "${PREDICTOR_DOCKER_URI}",
        )
