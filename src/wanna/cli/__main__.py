import logging
from enum import Enum
from pathlib import Path

import typer
from cookiecutter.main import cookiecutter

from wanna.core.loggers.wanna_logger import get_logger

from .plugins.runner import PluginRunner
from .version import perform_check

logger = get_logger(__name__)

logging.getLogger("smart_open").setLevel(logging.ERROR)
logging.getLogger("google").setLevel(logging.ERROR)
logging.getLogger("kfp").setLevel(logging.ERROR)

runner = PluginRunner()
app = runner.app


class WannaRepositoryTemplate(str, Enum):
    sklearn = "sklearn"
    blank = "blank"


@app.command(name="version")
def version(ctx: typer.Context):
    perform_check()


@app.command(name="init")
def init(
    ctx: typer.Context,
    output_dir: Path = typer.Option(
        ...,
        "--output-dir",
        prompt="Where do you want to initiate your wanna-ml repository? (input '.' to use the current directory)",
        help="The output directory where wanna-ml repository will be created",
    ),
    template: WannaRepositoryTemplate = typer.Option(
        WannaRepositoryTemplate.sklearn.value,
        "--template",
        "-t",
        help="Choose from available repository templates",
        show_choices=True,
    ),
):
    repository_templates = {
        WannaRepositoryTemplate.sklearn.value: "https://github.com/avast/wanna-ml-cookiecutter",
        WannaRepositoryTemplate.blank.value: "https://github.com/avast/wanna-blank-cookiecutter",
    }
    repository_template_url = repository_templates.get(template)
    result_dir = cookiecutter(repository_template_url, output_dir=output_dir)
    logger.user_success(f"Repo initiated at {result_dir}")


def wanna():
    """
    Main entrypoint for wanna cli
    """
    app()


if __name__ == "__main__":
    wanna()
