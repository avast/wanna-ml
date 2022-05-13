import pathlib
from pathlib import Path
from typing import Optional

import typer

from wanna.cli.plugins.base.base_plugin import BasePlugin
from wanna.cli.plugins.base.common_options import instance_name_option, profile_name_option, wanna_file_option
from wanna.cli.plugins.notebook.service import NotebookService
from wanna.cli.utils.config_loader import load_config_from_yaml


class NotebookPlugin(BasePlugin):
    """
    Main entry point for managing Workbench Notebooks on Vertex AI
    """

    def __init__(self) -> None:
        super().__init__()
        self.register_many(
            [
                self.delete,
                self.create,
                self.ssh,
            ]
        )

    @staticmethod
    def delete(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("notebook", "delete"),
    ) -> None:
        """
        Delete a User-Managed Workbench Notebook.
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        nb_service = NotebookService(config=config, workdir=workdir)
        nb_service.delete(instance_name)

    @staticmethod
    def create(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("notebook", "create"),
        owner: Optional[str] = typer.Option(None, "--owner", "-o", help=""),
    ) -> None:
        """
        Create a User-Managed Workbench Notebook.

        If there already is a notebook with the same name in the same location and project,
        you will be prompt if you want to delete the existing one and start a new one.

        When the notebook instance is created, you will be given a URL link to JupyterLab.
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        nb_service = NotebookService(config=config, workdir=workdir, owner=owner)
        nb_service.create(instance_name)

    @staticmethod
    def ssh(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option(
            "notebook",
            "ssh",
            help="Specify to which notebook you want to connect via ssh. "
            "Selecting 'all' will work only if there is just one notebook "
            "defined in your configuration, an error will be thrown otherwise.",
        ),
        run_in_background: bool = typer.Option(
            False,
            "--background/--interactive",
            "-b/-i",
            help="Interactive mode will start a bash directly in the Compute Engine instance "
            "backing the Jupyter notebook. "
            "Background mode serves more like a port-forwarding, "
            "you will be able to connect to the Jupyter Lab at localhost:{LOCAL_PORT}",
        ),
        local_port: int = typer.Option(
            8080, "--port", help="Jupyter Lab will be accessible at this port at localhost."
        ),
    ) -> None:
        """
        SSH connect to the Compute Engine instance that is behind the Jupyter Notebook.

        This will only work if the notebook is already running.

        Please note that you can connect to only one instance with one command call.
        If you have more notebooks defined in your YAML config, you have to select to which
        you want to connect to, instance_name "all" will be refused.

        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        nb_service = NotebookService(config=config, workdir=workdir)
        nb_service.ssh(instance_name, run_in_background, local_port)
