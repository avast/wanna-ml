import pathlib
from pathlib import Path
from typing import Optional

import typer

from wanna.cli.plugins.base.base_plugin import BasePlugin
from wanna.cli.plugins.base.common_options import wanna_file_option, instance_name_option, profile_option
from wanna.cli.plugins.notebook.service import NotebookService
from wanna.cli.utils.config_loader import load_config_from_yaml


class NotebookPlugin(BasePlugin):
    """
    Main entrypoint for managing Workbench Notebooks on Vertex AI
    """

    def __init__(self) -> None:
        super().__init__()
        self.register_many(
            [
                self.delete,
                self.create,
            ]
        )

    @staticmethod
    def delete(
        file: Path = wanna_file_option,
        profile_name: str = profile_option,
        instance_name: str = instance_name_option("notebook", "delete"),
    ) -> None:
        """
        Notebook delete command
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        nb_service = NotebookService(config=config, workdir=workdir)
        nb_service.delete(instance_name)

    @staticmethod
    def create(
        file: Path = wanna_file_option,
        profile_name: str = profile_option,
        instance_name: str = instance_name_option("notebook", "create"),
        owner: Optional[str] = typer.Option(None, "--owner", "-o", help=""),
    ) -> None:
        """
        Notebook create command
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        nb_service = NotebookService(config=config, workdir=workdir, owner=owner)
        nb_service.create(instance_name)
