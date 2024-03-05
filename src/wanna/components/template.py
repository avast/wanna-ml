from pathlib import Path

from cookiecutter.main import cookiecutter

from wanna.components import templates
from wanna.core.loggers.wanna_logger import get_logger

logger = get_logger(__name__)


def apply(output_dir: Path, no_input: bool = False):
    components_dir = Path(templates.__file__).parent.resolve()
    component_template_url = f"{components_dir}/base"
    result_dir = cookiecutter(
        component_template_url, output_dir=output_dir, no_input=no_input
    )
    logger.user_success(f"Component initiated at {result_dir}")
