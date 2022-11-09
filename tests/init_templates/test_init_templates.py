import os
from cookiecutter.main import cookiecutter
import shutil

import unittest

from wanna.core.models.gcp_profile import GCPProfileModel
from wanna.cli.__main__ import WannaRepositoryTemplate
from wanna.core.utils.config_loader import load_config_from_yaml


class TestInitTemplates:
    template_names = [t.value for t in WannaRepositoryTemplate]

    def tearDown(self):
        shutil.rmtree(os.path.join("testing", 'templates'))

    def test_templates_exist(self):
        for template_name in self.template_names:
            assert os.path.exists(os.path.join(os.getcwd(), 'templates', template_name))

    def _test_template(self, template_name: str):
        result_dir = cookiecutter("https://github.com/avast/wanna-ml.git",
                                  directory=f"templates/{template_name}",
                                  no_input=True,
                                  overwrite_if_exists=True,
                                  output_dir=os.path.join("testing", "templates", template_name))
        config = load_config_from_yaml(os.path.join(result_dir, "wanna.yaml"), "default")

    def test_templates(self):
        for template in self.template_names:
            self._test_template(template)
