from pathlib import Path
from typing import Optional

import typer

from wanna.cli.plugins.base_plugin import BasePlugin
from wanna.cli.plugins.common_options import (
    instance_name_option,
    profile_name_option,
    wanna_file_option,
)
from wanna.core.utils.config_loader import load_config_from_yaml


class TensorboardPlugin(BasePlugin):
    """
    Create, delete or list Tensorboard instances.
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
        Delete Tensorboard Instance in GCP Vertex AI Experiments.
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)

        # doing this import here speeds up the CLI app considerably
        from wanna.core.services.tensorboard import TensorboardService

        tb_service = TensorboardService(config=config)
        tb_service.delete(instance_name)

    @staticmethod
    def create(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("tensorboard", "create"),
    ) -> None:
        """
        Create Tensorboard Instance in GCP Vertex AI Experiments.

        If there already is a tensorboard with the same name in the same location and project,
        you will be prompt if you want to delete the existing one and start a new one.

        When the tensorboard instance is created, you will be given a full resource name.
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)

        # doing this import here speeds up the CLI app considerably
        from wanna.core.services.tensorboard import TensorboardService

        tb_service = TensorboardService(config=config)
        tb_service.create(instance_name)

    @staticmethod
    def list(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        region: Optional[str] = typer.Option(
            None,
            "--region",
            help="Overwrites the region from wanna-ml yaml configuration",
        ),
        filter_expr: str = typer.Option(
            None,
            "--filter",
            help="GCP filter expression for tensorboard instances. "
            "Read more on GCP filters on "
            "https://cloud.google.com/sdk/gcloud/reference/topic/filters \n"
            "Example: display_name=my-tensorboard. \n"
            "Example: labels.wanna_project:* - to show all tensorboard created by wanna-ml.\n"
            "Example: labels.wanna_project:sushi-ssl.",
        ),
        show_url: bool = typer.Option(
            True, "--url/--no-url", help="Weather to show URL link to experiments"
        ),
    ) -> None:
        """
        List Tensorboard Instances in GCP Vertex AI Experiments.

        We also show Tensorboard Experiments and Tensorboard Runs for each Instance
        in the tree format.
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)

        # doing this import here speeds up the CLI app considerably
        from wanna.core.services.tensorboard import TensorboardService

        tb_service = TensorboardService(config=config)
        region = region or config.gcp_profile.region
        if not region:
            raise ValueError(
                "Please provide a region. Either via cli arg or via region or zone in selected gcp profile"
            )
        else:
            tb_service.list_tensorboards_in_tree(
                region=region, filter_expr=filter_expr, show_url=show_url
            )
