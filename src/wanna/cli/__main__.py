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


class WannaRepositoryTemplate(Enum):
    sklearn = "sklearn"
    blank = "blank"


@app.command(name="version", help="Print your current and latest available version")
def version():
    perform_check()


@app.command(name="init", help="Initiate a new wanna-ml project from template.")
def init(
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
    result_dir = cookiecutter(
        "https://github.com/avast/wanna-ml",
        directory=f"templates/{template}",
        output_dir=output_dir,
    )
    logger.user_success(f"Repo initiated at {result_dir}")


def wanna():
    """
    Main entrypoint for wanna cli
    """
    app()


if __name__ == "__main__":
    wanna()
