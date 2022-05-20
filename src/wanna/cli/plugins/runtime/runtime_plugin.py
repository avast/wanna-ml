import pathlib
from pathlib import Path
from typing import Optional

import typer

from wanna.cli.plugins.base.base_plugin import BasePlugin
from wanna.cli.plugins.base.common_options import instance_name_option, profile_name_option, wanna_file_option
from wanna.cli.plugins.runtime.service import RuntimeService
from wanna.cli.utils.config_loader import load_config_from_yaml


class RuntimePlugin(BasePlugin):
    """
    Main entry point for managing Workbench Notebooks on Vertex AI
    """

    def __init__(self) -> None:
        super().__init__()
        self.register_many([self.delete, self.create])

    @staticmethod
    def delete(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("runtime", "delete"),
    ) -> None:
        """
        Delete a Managed Notebook in Vertex AI.
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        runtime_service = RuntimeService(config=config, workdir=workdir)
        runtime_service.delete(instance_name)

    @staticmethod
    def create(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("runtime", "create"),
        owner: Optional[str] = typer.Option(None, "--owner", "-o", help=""),
    ) -> None:
        """
        Create a Managed Notebook in Vertex AI.

        If there already is a notebook with the same name in the same location and project,
        you will be prompt if you want to delete the existing one and start a new one.

        When the managed notebook is created, you will be given a URL link to JupyterLab.
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        runtime_service = RuntimeService(config=config, workdir=workdir, owner=owner)
        runtime_service.create(instance_name)
