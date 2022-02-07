import typer

from pathlib import Path
from wanna.cli.plugins.base import BasePlugin
from wanna.cli.plugins.notebook.service import NotebookService


class NotebookPlugin(BasePlugin):
    """
    Main entrypoint for managing Workbench Notebooks on Vertex AI
    """

    def __init__(self) -> None:
        super(NotebookPlugin, self).__init__()
        self.register_many(
            [
                self.expose_context,
                self.call_everything,
                self.hello,
                self.goodbye,
                self.create
            ]
        )

        # add some nesting with `sub-notebook-command` command.
        # self.app.add_typer(SubNotebookPlugin().app, name='sub-notebook-command')

    @staticmethod
    def hello(name: str) -> None:
        """
        Notebook hello command
        """
        typer.echo(f"Hello Notebook, {name}")

    @staticmethod
    def goodbye(name: str) -> None:
        typer.echo(f"Goodbye Notebook, {name}")

    @staticmethod
    def create(
            file: Path = typer.Option("wanna.yaml", help="Path to the wanna-ml yaml configuration")
    ) -> None:
        """
        Notebook create command
        """
        typer.echo(f"Let us create a notebook from {file}")
        nb = NotebookService(file)
        nb.load_notebook_service()
        print(nb.notebooks_instances)


    @staticmethod
    def expose_context(ctx: typer.Context) -> None:
        typer.echo(f"The command from context is: {ctx.command}")

    def call_everything(self, ctx: typer.Context, name: str) -> None:
        self.hello(name)
        self.expose_context(ctx)
        self.goodbye(name)
