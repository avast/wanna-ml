import logging
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
    template: str = typer.Option(
        ...,
        "--template",
        "-t",
        help="The git repository of the template you want to use",
    ),
    checkout: str | None = typer.Option(
        None,
        "--checkout",
        "-c",
        help="The branch, tag or commit to checkout after cloning the repository",
    ),
    directory: str | None = typer.Option(
        None,
        "--directory",
        "-d",
        help="The directory within the repository to use as the template",
    ),
    overwrite_if_exists: bool = typer.Option(
        False,
        "--overwrite-if-exists",
        help="Overwrite the contents of the output directory if it exists",
    ),
    no_input: bool = typer.Option(
        False,
        "--no-input",
        help="Do not prompt for parameters and only use cookiecutter.json file content",
    ),
):
    result_dir = cookiecutter(
        template=template,
        checkout=checkout,
        directory=directory,
        output_dir=output_dir,
        overwrite_if_exists=overwrite_if_exists,
        no_input=no_input,
    )
    logger.user_success(f"Repo initiated at {result_dir}")


def wanna():
    """
    Main entrypoint for wanna cli
    """
    app()


if __name__ == "__main__":
    wanna()
