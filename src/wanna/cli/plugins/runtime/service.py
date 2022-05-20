import subprocess
from pathlib import Path
from typing import List, Optional

import typer
from google.api_core import exceptions
from google.cloud import notebooks_v1
from google.cloud.notebooks_v1.types import Runtime
from waiting import wait

from wanna.cli.docker.service import DockerService
from wanna.cli.models.runtime import RuntimeModel
from wanna.cli.models.wanna_config import WannaConfigModel
from wanna.cli.plugins.base.service import BaseService
from wanna.cli.plugins.tensorboard.service import TensorboardService
from wanna.cli.utils import templates
from wanna.cli.utils.gcp.gcp import construct_vm_image_family_from_vm_image, upload_string_to_gcs
from wanna.cli.utils.spinners import Spinner


class RuntimeService(BaseService):
    def __init__(
        self,
        config: WannaConfigModel,
        workdir: Path,
        owner: Optional[str] = None,
        version: str = "dev",
    ):
        super().__init__(
            instance_type="runtime",
            instance_model=RuntimeModel,
        )
        self.version = version
        self.instances = config.notebooks
        self.wanna_project = config.wanna_project
        self.bucket_name = config.gcp_profile.bucket
        self.runtime_client = notebooks_v1.ManagedNotebookServiceClient()
        self.config = config
        self.docker_service = (
            DockerService(
                docker_model=config.docker,
                gcp_profile=config.gcp_profile,
                version=version,
                work_dir=workdir,
                wanna_project_name=self.wanna_project.name,
            )
            if config.docker
            else None
        )

        self.owner = owner
        self.tensorboard_service = TensorboardService(config=config)

    def _list_runtimes(self, project_id: str, location: str) -> List[str]:
        """
        List all managed notebooks with given project_id and location.

        Args:
            project_id: GCP project ID
            location: GCP location (zone)

        Returns:
            runtime_names: List of the full names of managed notebook (this includes project_id, and region)

        """
        runtimes = self.runtime_client.list_runtimes(parent=f"projects/{project_id}/locations/{location}")
        runtime_names = [i.name for i in runtimes]
        return runtime_names

    def _instance_exists(self, runtime: RuntimeModel) -> bool:
        """
        Check if the instance with given instance_name exists in given GCP project project_id and location.
        Args:
            instance: notebook to verify if exists on GCP

        Returns:
            True if exists, False if not
        """

        full_runtime_name = f"projects/{runtime.project_id}/locations/{runtime.region}/runtimes/{runtime.runtime_id}"
        return full_runtime_name in self._list_runtimes(runtime.project_id, runtime.region)

    def _delete_one_instance(self, runtime: RuntimeModel) -> None:
        """
        Delete one managed notebook. This assumes that it has been already verified that the managed notebook exists.

        Args:
            runtime: managed notebook to be deleted
        """

        exists = self._instance_exists(runtime)
        if exists:
            with Spinner(text=f"Deleting {self.instance_type} {runtime.runtime_id}"):
                deleted = self.runtime_client.delete_runtime(
                    name=f"projects/{runtime.project_id}/locations/" f"{runtime.region}/runtimes/{runtime.runtime_id}"
                )
                deleted.result()
        else:
            typer.secho(
                f"Runtime with name {runtime.runtime_id} was not found in region {runtime.region}",
                fg=typer.colors.RED,
            )

    def _validate_jupyterlab_state(self, name: str, state: int) -> bool:
        """
        Validate if the given runtime is in given state.

        Args:
            name: projects/{runtime.project_id}/locations/{runtime.region}/runtimes/{runtime.runtime_id}
            state: Managed Notebook state (ACTIVE, PENDING,...)

        Returns:
            True if desired state, False otherwise
        """
        try:
            runtime = self.runtime_client.get_runtime(name=name)
        except exceptions.NotFound:
            raise exceptions.NotFound(f"Notebook {name} was not found.") from None
        return runtime.state == state

    def _get_jupyterlab_link(self, name: str) -> str:
        """
        Get a link to jupyterlab proxy based on given runtime full name.
        Args:
            name: projects/{project_id}/locations/{location}/runtimes/{runtime_id}

        Returns:
            proxy_uri: link to jupyterlab
        """
        runtime = self.runtime_client.get_runtime({"name": name})
        return f"https://{runtime.proxy_uri}"

    def _create_one_instance(self, runtime: RuntimeModel, **kwargs) -> None:
        """
        Create a managed notebook based on information in RuntimeModel class.
        1. Check if the managed notebook already exists
        2. Parse the information from RuntimeModel to GCP API friendly format = instance_request
        3. Wait for the runtime to start
        4. Wait for JupyterLab to start
        5. Get and print the link to JupyterLab

        Args:
            runtime: managed notebook to be created

        """
        exists = self._instance_exists(runtime)
        if exists:
            typer.echo(f"Managed notebook {runtime.runtime_id} already exists in location {runtime.region}")
            should_recreate = typer.confirm("Are you sure you want to delete it and start a new?")
            if should_recreate:
                self._delete_one_instance(runtime)
            else:
                return
        with Spinner(text=f"Starting up the runtime for {runtime.runtime_id}"):
            operation = self.runtime_client.create_runtime(
                parent=f"projects/{runtime.project_id}/locations/{runtime.region}",
                runtime_id=runtime.runtime_id,
                runtime=Runtime(),
            )
            runtime_full_name = operation.result().name
        with Spinner(text="Starting JupyterLab"):
            wait(
                lambda: self._validate_jupyterlab_state(runtime_full_name, Runtime.State.ACTIVE),
                timeout_seconds=450,
                sleep_seconds=20,
                waiting_for="Starting JupyterLab...",
            )
            jupyterlab_link = self._get_jupyterlab_link(runtime_full_name)
        typer.echo(f"\N{party popper} JupyterLab started at {jupyterlab_link}")
