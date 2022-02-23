from pathlib import Path

import typer
from wanna.cli.plugins.base.base_plugin import BasePlugin
from wanna.cli.plugins.tensorboard.service import TensorboardService


class TensorboardPlugin(BasePlugin):
    """
    Main entrypoint for managing Vertex AI Tensorboards
    """

    def __init__(self) -> None:
        super().__init__()
        self.register_many(
            [
                self.delete,
                self.create,
            ]
        )

        # add some nesting with `sub-notebook-command` command.
        # self.app.add_typer(SubNotebookPlugin().app, name='sub-notebook-command')

    @staticmethod
    def delete(
        file: Path = typer.Option(
            "wanna.yaml", "--file", "-f", help="Path to the wanna-ml yaml configuration"
        ),
        instance_name: str = typer.Option(
            "all",
            "--name",
            "-n",
            help="Specify only one tensorboard from your wanna-ml yaml configuration to delete. "
            "Choose 'all' to delete all tensorboards.",
        ),
    ) -> None:
        """
        Tensorboard delete command
        """
        tb_service = TensorboardService()
        tb_service.load_config_from_yaml(file)
        tb_service.delete(instance_name)

    @staticmethod
    def create(
        file: Path = typer.Option(
            "wanna.yaml", "--file", "-f", help="Path to the wanna-ml yaml configuration"
        ),
        instance_name: str = typer.Option(
            "all",
            "--name",
            "-n",
            help="Specify only one tensorboard from your wanna-ml yaml configuration to create. "
            "Choose 'all' to create all tensorboards.",
        ),
    ) -> None:
        """
        Tensorboard create command
        """
        tb_service = TensorboardService()
        tb_service.load_config_from_yaml(file)
        tb_service.create(instance_name)
