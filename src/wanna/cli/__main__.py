import logging
from pathlib import Path

import typer
from cookiecutter.main import cookiecutter

from wanna.cli.utils.spinners import Spinner

from .plugins.runner import PluginRunner
from .version import perform_check

logging.getLogger("smart_open").setLevel(logging.ERROR)
logging.getLogger("google").setLevel(logging.ERROR)
logging.getLogger("kfp").setLevel(logging.ERROR)

runner = PluginRunner()
app = runner.app


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
):
    wanna_git_repository = "https://git.int.avast.com/bds/wanna-ml-cookiecutter"
    result_dir = cookiecutter(wanna_git_repository, output_dir=output_dir)
    Spinner(text=f"Repo initiated at {result_dir}").succeed()


def wanna():
    """
    Main entrypoint for wanna cli
    """
    app()


if __name__ == "__main__":
    wanna()
