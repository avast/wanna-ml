from pathlib import Path

import typer

from wanna.cli.plugins.base.base_plugin import BasePlugin
from wanna.cli.plugins.base.common_options import instance_name_option, profile_name_option, wanna_file_option
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
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("tensorboard", "delete"),
    ) -> None:
        """
        Tensorboard delete command
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        tb_service = TensorboardService(config=config)
        tb_service.delete(instance_name)

    @staticmethod
    def create(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("tensorboard", "create"),
    ) -> None:
        """
        Tensorboard create command
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        tb_service = TensorboardService(config=config)
        tb_service.create(instance_name)

    @staticmethod
    def list(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        region: str = typer.Option(None, "--region", help="Overwrites the region from wanna-ml yaml configuration"),
        filter_expr: str = typer.Option(None, "--filter", help="GCP filter expression for tensorboard instances"),
        show_url: bool = typer.Option(True, "--url/--no-url", help="Weather to show URL link to experiments"),
    ) -> None:
        """
        Tensorboard create command
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        tb_service = TensorboardService(config=config)
        tb_service.list_tensorboards_in_tree(
            region=region or config.gcp_profile.region, filter_expr=filter_expr, show_url=show_url
        )
