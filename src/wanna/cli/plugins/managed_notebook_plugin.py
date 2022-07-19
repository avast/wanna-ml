import pathlib
from pathlib import Path

import typer

from wanna.cli.plugins.base_plugin import BasePlugin
from wanna.cli.plugins.common_options import instance_name_option, profile_name_option, wanna_file_option
from wanna.core.services.managed_notebook import ManagedNotebookService
from wanna.core.utils.config_loader import load_config_from_yaml


class ManagedNotebookPlugin(BasePlugin):
    """
    Main entry point for managing Workbench Notebooks on Vertex AI
    """

    def __init__(self) -> None:
        super().__init__()
        self.register_many(
            [
                self.delete,
                self.create,
                self.sync,
                self.report,
                self.build,
            ]
        )

    @staticmethod
    def delete(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("managed_notebook", "delete"),
    ) -> None:
        """
        Delete a Managed Workbench Notebook.
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        nb_service = ManagedNotebookService(config=config, workdir=workdir)
        nb_service.delete(instance_name)

    @staticmethod
    def create(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("managed_notebook", "create"),
    ) -> None:
        """
        Create a Managed Workbench Notebook.

        If there already is a notebook with the same name in the same location and project,
        you will be prompt if you want to delete the existing one and start a new one.

        When the notebook instance is created, you will be given a URL link to JupyterLab.
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        nb_service = ManagedNotebookService(config=config, workdir=workdir)
        nb_service.create(instance_name)

    @staticmethod
    def sync(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        force: bool = typer.Option(False, "--force", help="Synchronisation without prompt"),
    ) -> None:
        """
        Synchronize existing Managed Notebooks with wanna.yaml

        1. Reads current notebooks where label is defined per field wanna_project.name in wanna.yaml
        2. Does a diff between what is on GCP and what is on yaml
        3. Create the ones defined in yaml and missing in GCP
        4. Delete the ones in GCP that are not in wanna.yaml
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        nb_service = ManagedNotebookService(config=config, workdir=workdir)
        nb_service.sync(force)

    @staticmethod
    def report(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("managed_notebook", "report"),
    ) -> None:
        """
        Displays a link to the cost report per wanna_project and optionally per instance name
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        nb_service = ManagedNotebookService(config=config, workdir=workdir)
        nb_service.report(
            instance_name=instance_name,
            wanna_project=config.wanna_project.name,
            wanna_resource="managed_notebook",
            gcp_project=config.gcp_profile.project_id,
            billing_id=config.wanna_project.billing_id,
            organization_id=config.wanna_project.organization_id,
        )

    @staticmethod
    def build(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
    ) -> None:
        """
        Validates build of notebooks as they are defined in wanna.yaml
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        nb_service = ManagedNotebookService(config=config, workdir=workdir)
        nb_service.build()
