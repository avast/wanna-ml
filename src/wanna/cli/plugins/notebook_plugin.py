import pathlib
from pathlib import Path
from typing import Optional

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


class NotebookPlugin(BasePlugin):
    """
    Create, delete and more operations for user-managed Workbench (Jupyter notebook).
    """

    def __init__(self) -> None:
        super().__init__()
        self.register_many(
            [
                self.delete,
                self.create,
                self.ssh,
                self.report,
                self.build,
                self.push,
                self.sync,
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

        # doing this import here speeds up the CLI app considerably
        from wanna.core.services.notebook import NotebookService

        nb_service = NotebookService(config=config, workdir=workdir)
        nb_service.delete(instance_name)

    @staticmethod
    def create(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("notebook", "create"),
        owner: Optional[str] = typer.Option(None, "--owner", "-o", help=""),
        version: str = version_option(instance_type="notebook"),
        mode: PushMode = push_mode_option,
    ) -> None:
        """
        Create a User-Managed Workbench Notebook.

        If there already is a notebook with the same name in the same location and project,
        you will be prompt if you want to delete the existing one and start a new one.

        When the notebook instance is created, you will be given a URL link to JupyterLab.
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()

        # doing this import here speeds up the CLI app considerably
        from wanna.core.services.notebook import NotebookService

        nb_service = NotebookService(
            config=config, workdir=workdir, owner=owner, version=version
        )
        nb_service.create(instance_name, push_mode=mode)

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
            8080,
            "--port",
            help="Jupyter Lab will be accessible at this port at localhost.",
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

        # doing this import here speeds up the CLI app considerably
        from wanna.core.services.notebook import NotebookService

        nb_service = NotebookService(config=config, workdir=workdir)
        nb_service.ssh(instance_name, run_in_background, local_port)

    @staticmethod
    def report(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("notebook", "report"),
    ) -> None:
        """
        Displays a link to the cost report per wanna_project and optionally per instance name.
        """

        # doing this import here speeds up the CLI app considerably

        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()

        # doing this import here speeds up the CLI app considerably
        from wanna.core.services.notebook import NotebookService

        nb_service = NotebookService(config=config, workdir=workdir)

        nb_service.report(
            instance_name=instance_name,
            wanna_project=config.wanna_project.name,
            wanna_resource="notebook",
            gcp_project=config.gcp_profile.project_id,
            billing_id=config.wanna_project.billing_id,
            organization_id=config.wanna_project.organization_id,
        )

    @staticmethod
    def build(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        version: str = version_option(instance_type="notebook"),
    ) -> None:
        """
        Validates build of notebooks as they are defined in wanna.yaml
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()

        # doing this import here speeds up the CLI app considerably
        from wanna.core.services.notebook import NotebookService

        nb_service = NotebookService(config=config, workdir=workdir, version=version)
        nb_service.build()

    @staticmethod
    def push(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("notebook", "push"),
        version: str = version_option(instance_type="notebook"),
        mode: PushMode = typer.Option(
            PushMode.containers,
            "--mode",
            "-m",
            help="Notebook push mode, due to CI/CD not "
            "allowing to push to docker registry from "
            "GCP Agent, we need to split it. "
            "Notebooks currently support only containers, as we do not create manifests as of now.",
        ),
    ) -> None:
        """
        Push docker containers. This command also builds the images.
        """

        # doing this import here speeds up the CLI app considerably

        if mode != PushMode.containers:
            logger.user_error("Only containers are supported push mode as of now.")
            typer.Exit(1)

        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()

        # doing this import here speeds up the CLI app considerably
        from wanna.core.services.notebook import NotebookService

        nb_service = NotebookService(config=config, workdir=workdir, version=version)
        nb_service.push(instance_name=instance_name)

    @staticmethod
    def sync(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        force: bool = typer.Option(
            False, "--force", help="Synchronisation without prompt"
        ),
        version: str = version_option(instance_type="notebook"),
        mode: PushMode = push_mode_option,
    ) -> None:
        """
        Synchronize existing User-managed Notebooks with wanna.yaml

        1. Reads current notebooks where label is defined per field wanna_project.name in wanna.yaml
        2. Does a diff between what is on GCP and what is on yaml
        3. Create the ones defined in yaml and missing in GCP
        4. Delete the ones in GCP that are not in wanna.yaml
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()

        # doing this import here speeds up the CLI app considerably
        from wanna.core.services.notebook import NotebookService

        nb_service = NotebookService(config=config, workdir=workdir, version=version)
        nb_service.sync(force=force, push_mode=mode)
