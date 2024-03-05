import typer

from wanna.cli.plugins.components_plugin import ComponentsPlugin
from wanna.cli.plugins.job_plugin import JobPlugin
from wanna.cli.plugins.managed_notebook_plugin import ManagedNotebookPlugin
from wanna.cli.plugins.notebook_plugin import NotebookPlugin
from wanna.cli.plugins.pipeline_plugin import PipelinePlugin
from wanna.cli.plugins.tensorboard_plugin import TensorboardPlugin


class PluginRunner:
    def __init__(self) -> None:
        self.app = typer.Typer(
            rich_markup_mode="rich", help="Complete MLOps framework for Vertex-AI"
        )

        typers = [
            ("pipeline", PipelinePlugin()),
            ("job", JobPlugin()),
            ("notebook", NotebookPlugin()),
            ("tensorboard", TensorboardPlugin()),
            ("managed-notebook", ManagedNotebookPlugin()),
            ("components", ComponentsPlugin()),
        ]
        for name, subcommand in typers:
            self.app.add_typer(subcommand.app, name=name, help=subcommand.__doc__)
