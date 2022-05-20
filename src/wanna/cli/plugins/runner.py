import typer

from .job.job_plugin import JobPlugin
from .notebook.notebook_plugin import NotebookPlugin
from .pipeline.pipeline_plugin import PipelinePlugin
from .runtime.runtime_plugin import RuntimePlugin
from .tensorboard.tensorboard_plugin import TensorboardPlugin


class PluginRunner:
    def __init__(self) -> None:
        self.app = typer.Typer()

        typers = [
            ("pipeline", PipelinePlugin()),
            ("job", JobPlugin()),
            ("notebook", NotebookPlugin()),
            ("tensorboard", TensorboardPlugin()),
            ("runtime", RuntimePlugin()),
        ]
        for name, subcommand in typers:
            self.app.add_typer(subcommand.app, name=name)
