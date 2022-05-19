import os
import pathlib
import shutil
import unittest

from wanna.cli.plugins.components.service import ComponentsService


class TestWannaComponentsService(unittest.TestCase):
    parent = pathlib.Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
    pipeline_build_dir = parent / "build" / "components"

    def test_wanna_components_service(self):
        shutil.rmtree(self.pipeline_build_dir, ignore_errors=True)
        service = ComponentsService(self.pipeline_build_dir)
        service.apply_template(no_input=True)
        component_dir = self.pipeline_build_dir / "component_name"
        self.assertTrue(component_dir.exists())
