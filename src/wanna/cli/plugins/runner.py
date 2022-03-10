import typer

from .job.command import JobCommand
from .notebook_plugin import NotebookPlugin
from .pipeline_plugin import PipelinePlugin


class PluginRunner:
    def __init__(self) -> None:
        self.app = typer.Typer()

        typers = [
            ("pipeline", PipelinePlugin()),
            ("job", JobCommand()),
            ("notebook", NotebookPlugin()),
        ]
        for name, subcommand in typers:
            self.app.add_typer(subcommand.app, name=name)

    def run(self) -> None:
        self.app()
