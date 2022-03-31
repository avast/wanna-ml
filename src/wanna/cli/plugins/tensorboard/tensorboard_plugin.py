from pathlib import Path

import typer

from wanna.cli.plugins.base.base_plugin import BasePlugin
from wanna.cli.plugins.tensorboard.service import TensorboardService
from wanna.cli.utils.config_loader import load_config_from_yaml


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
                self.list,
            ]
        )

        # add some nesting with `sub-notebook-command` command.
        # self.app.add_typer(SubNotebookPlugin().app, name='sub-notebook-command')

    @staticmethod
    def delete(
        file: Path = typer.Option("wanna.yaml", "--file", "-f", help="Path to the wanna-ml yaml configuration"),
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
        config = load_config_from_yaml(file)
        tb_service = TensorboardService(config=config)
        tb_service.delete(instance_name)

    @staticmethod
    def create(
        file: Path = typer.Option("wanna.yaml", "--file", "-f", help="Path to the wanna-ml yaml configuration"),
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
        config = load_config_from_yaml(file)
        tb_service = TensorboardService(config=config)
        tb_service.create(instance_name)

    @staticmethod
    def list(
        file: Path = typer.Option("wanna.yaml", "--file", "-f", help="Path to the wanna-ml yaml configuration"),
        region: str = typer.Option(None, "--region", help="Overwrites the region from wanna-ml yaml configuration"),
        filter_expr: str = typer.Option(None, "--filter", help="GCP filter expression for tensorboard instances"),
        show_url: bool = typer.Option(True, "--url/--no-url", help="Weather to show URL link to experiments"),
    ) -> None:
        """
        Tensorboard create command
        """
        config = load_config_from_yaml(file)
        tb_service = TensorboardService(config=config)
        tb_service.list_tensorboards_in_tree(
            region=region or config.gcp_settings.region, filter_expr=filter_expr, show_url=show_url
        )
