import logging

import typer

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


def wanna():
    """
    Main entrypoint for wanna cli
    """
    app()


if __name__ == "__main__":
    wanna()
