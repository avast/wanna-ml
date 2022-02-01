import typer

from .job.job_plugin import JobPlugin
from .notebook.notebook_plugin import NotebookPlugin
from .pipeline.pipeline_plugin import PipelinePlugin


class PluginRunner:
    def __init__(self) -> None:
        self.app = typer.Typer()

        my_typers = [
            ("pipeline", PipelinePlugin()),
            ("job", JobPlugin()),
            ("notebook", NotebookPlugin()),
        ]
        for name, subcommand in my_typers:
            self.app.add_typer(subcommand.app, name=name)

    def run(self) -> None:
        self.app()
