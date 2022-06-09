from pathlib import Path

from cookiecutter.main import cookiecutter

from wanna.components import templates
from wanna.core.utils.spinners import Spinner


class ComponentsService:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def apply_template(self, no_input: bool = False):
        components_dir = Path(templates.__file__).parent.resolve()
        component_template_url = f"{components_dir}/base"
        result_dir = cookiecutter(component_template_url, output_dir=self.output_dir, no_input=no_input)
        Spinner(text=f"Component initiated at {result_dir}").succeed()
