from pathlib import Path

import typer
from wanna.cli.plugins.base.base_plugin import BasePlugin
from wanna.cli.plugins.notebook.service import NotebookService


class NotebookPlugin(BasePlugin):
    """
    Main entrypoint for managing Workbench Notebooks on Vertex AI
    """

    def __init__(self) -> None:
        super().__init__()
        self.register_many(
            [
                self.expose_context,
                self.call_everything,
                self.hello,
                self.delete,
                self.create,
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
    def delete(
        file: Path = typer.Option(
            "wanna.yaml", "--file", "-f", help="Path to the wanna-ml yaml configuration"
        ),
        instance_name: str = typer.Option(
            "all",
            "--name",
            "-n",
            help="Specify only one notebook from your wanna-ml yaml configuration to delete. "
            "Choose 'all' to delete all notebooks.",
        ),
    ) -> None:
        """
        Notebook delete command
        """
        nb_service = NotebookService()
        nb_service.load_config_from_yaml(file)
        nb_service.delete(instance_name)

    @staticmethod
    def create(
        file: Path = typer.Option(
            "wanna.yaml", "--file", "-f", help="Path to the wanna-ml yaml configuration"
        ),
        instance_name: str = typer.Option(
            "all",
            "--name",
            "-n",
            help="Specify only one notebook from your wanna-ml yaml configuration to create. "
            "Choose 'all' to create all notebooks.",
        ),
    ) -> None:
        """
        Notebook create command
        """
        nb_service = NotebookService()
        nb_service.load_config_from_yaml(file)
        nb_service.create(instance_name)

    @staticmethod
    def expose_context(ctx: typer.Context) -> None:
        typer.echo(f"The command from context is: {ctx.command}")

    def call_everything(self, ctx: typer.Context, name: str) -> None:
        self.hello(name)
        self.expose_context(ctx)
