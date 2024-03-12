import pathlib
from pathlib import Path

import typer

from wanna.cli.plugins.base_plugin import BasePlugin
from wanna.cli.plugins.common_options import (
    instance_name_option,
    profile_name_option,
    push_mode_option,
    version_option,
    wanna_file_option,
)
from wanna.core.deployment.models import PushMode
from wanna.core.loggers.wanna_logger import get_logger
from wanna.core.utils.config_loader import load_config_from_yaml

logger = get_logger(__name__)


class ManagedNotebookPlugin(BasePlugin):
    """
    Create, delete and more operations for managed Workbench (Jupyter notebook).
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
                self.push,
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

        # doing this import here speeds up the CLI app considerably
        from wanna.core.services.managed_notebook import ManagedNotebookService

        nb_service = ManagedNotebookService(config=config, workdir=workdir)
        nb_service.delete(instance_name)

    @staticmethod
    def create(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("managed_notebook", "create"),
        version: str = version_option(instance_type="managed notebook"),
        mode: PushMode = push_mode_option,
    ) -> None:
        """
        Create a Managed Workbench Notebook.

        If there already is a notebook with the same name in the same location and project,
        you will be prompt if you want to delete the existing one and start a new one.

        When the notebook instance is created, you will be given a URL link to JupyterLab.
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()

        # doing this import here speeds up the CLI app considerably
        from wanna.core.services.managed_notebook import ManagedNotebookService

        nb_service = ManagedNotebookService(
            config=config, workdir=workdir, version=version
        )
        nb_service.create(instance_name, push_mode=mode)

    @staticmethod
    def sync(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        force: bool = typer.Option(
            False, "--force", help="Synchronisation without prompt"
        ),
        version: str = version_option(instance_type="managed notebook"),
        mode: PushMode = push_mode_option,
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

        # doing this import here speeds up the CLI app considerably
        from wanna.core.services.managed_notebook import ManagedNotebookService

        nb_service = ManagedNotebookService(
            config=config, workdir=workdir, version=version
        )
        nb_service.sync(force=force, push_mode=mode)

    @staticmethod
    def report(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("managed_notebook", "report"),
    ) -> None:
        """
        Displays a link to the cost report per wanna_project and optionally per instance name.
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()

        # doing this import here speeds up the CLI app considerably
        from wanna.core.services.managed_notebook import ManagedNotebookService

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
        version: str = version_option(instance_type="managed notebook"),
    ) -> None:
        """
        Validates build of notebooks as they are defined in wanna.yaml.
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()

        # doing this import here speeds up the CLI app considerably
        from wanna.core.services.managed_notebook import ManagedNotebookService

        nb_service = ManagedNotebookService(
            config=config, workdir=workdir, version=version
        )
        nb_service.build()

    @staticmethod
    def push(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("managed notebook", "push"),
        version: str = version_option(instance_type="managed notebook"),
        mode: PushMode = typer.Option(
            PushMode.containers,
            "--mode",
            "-m",
            help="Managed-Notebook push mode, due to CI/CD not "
            "allowing to push to docker registry from "
            "GCP Agent, we need to split it. "
            "Notebooks currently support only containers, as we do not create manifests as of now.",
        ),
    ) -> None:
        """
        Push docker containers. This command also builds the images.
        """
        if mode != PushMode.containers:
            logger.user_error("Only containers are supported push mode as of now.")
            typer.Exit(1)

        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()

        # doing this import here speeds up the CLI app considerably
        from wanna.core.services.managed_notebook import ManagedNotebookService

        nb_service = ManagedNotebookService(
            config=config, workdir=workdir, version=version
        )
        nb_service.push(instance_name=instance_name)
