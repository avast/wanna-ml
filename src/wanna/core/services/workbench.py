from abc import abstractmethod
from typing import TypeVar, Union

import typer
from google.api_core import exceptions
from google.api_core.operation import Operation
from google.cloud.notebooks_v1 import CreateInstanceRequest as CreateInstanceRequestV1
from google.cloud.notebooks_v1 import CreateRuntimeRequest, Runtime
from google.cloud.notebooks_v1 import Instance as InstanceV1
from google.cloud.notebooks_v2 import CreateInstanceRequest, Instance
from waiting import wait

from wanna.core.deployment.models import PushMode
from wanna.core.loggers.wanna_logger import get_logger
from wanna.core.models.workbench import BaseWorkbenchModel
from wanna.core.services.base import BaseService

T = TypeVar("T", bound=BaseWorkbenchModel)
CreateRequest = Union[CreateRuntimeRequest, CreateInstanceRequestV1, CreateInstanceRequest]
Instances = Union[Runtime, InstanceV1, Instance]

logger = get_logger(__name__)


class BaseWorkbenchService(BaseService[T]):
    @abstractmethod
    def _instance_exists(self, instance: T) -> bool:
        """
        Check if the instance with given instance_name exists in given GCP project project_id and location.
        Args:
            instance: notebook to verify if exists on GCP

        Returns:
            True if exists, False if not
        """

    def _create_one_instance(self, instance: T, **kwargs) -> None:
        """
        Create a notebook instance based on information in NotebookModel class.
        1. Check if the notebook already exists
        2. Parse the information from NotebookModel to GCP API friendly format = runtime_request
        3. Wait for the compute instance behind the notebook to start
        4. Wait for JupyterLab to start
        5. Get and print the link to JupyterLab

        Args:
            instance: notebook to be created

        """
        should_end = self._create_one_instance_exists(instance)
        if should_end:
            return
        push_mode: PushMode = kwargs.get("push_mode")  # type: ignore
        request = self._create_instance_request(
            instance=instance, deploy=True, push_mode=push_mode
        )
        logger.user_info(f"Creating underlying compute engine instance for {instance.name} ...")
        nb_instance = self._create_instance_client(request=request)
        instance_full_name = (
            nb_instance.result().name
        )  # .result() waits for compute engine behind the notebook to start
        logger.user_info(f"Starting JupyterLab for {instance.name} ...")
        wait(
            lambda: self._validate_jupyterlab_state(instance_full_name, Runtime.State.ACTIVE),
            timeout_seconds=450,
            sleep_seconds=20,
            waiting_for="Starting JupyterLab in your instance",
        )
        jupyterlab_link = self._get_jupyterlab_link(instance_full_name)
        logger.user_success(f"JupyterLab for {instance.name} started at {jupyterlab_link}")

    def _create_one_instance_exists(self, instance: T) -> bool:
        """
        Checks if the instance already exists and prompts the user to delete it if it does.

        Args:
            instance: Workbench instance to check.

        Returns:
            should_end: True if the method should end.
        """
        exists = self._instance_exists(instance)
        if exists:
            logger.user_info(
                f"{self.instance_type} {instance.name} already exists in location {self.workbench_location(instance)}"
            )
            should_recreate = typer.confirm("Are you sure you want to delete it and start a new?")
            if should_recreate:
                self._delete_one_instance(instance)
            else:
                return True
        return False

    @abstractmethod
    def workbench_location(self, instance: T) -> str:
        """
        Args:
            instance: workbench instance.

        Returns:
            location: Return the location of the workbench instance, either region or zone.
        """

    @abstractmethod
    def _create_instance_request(
        self,
        instance: T,
        deploy: bool = True,
        push_mode: PushMode = PushMode.all,
    ) -> CreateRequest:
        """
        Transform the information about desired notebook from our NotebookModel model (based on yaml config)
        to the form suitable for GCP API.

        Args:
            instance: Workbench instance to create.
            deploy: If True, deploy the instance.
            push_mode: Push mode to use.

        Returns:
            request: Return the instance creation request.
        """

    def _delete_one_instance(self, instance: T) -> None:
        """
        Delete one notebook instance. This assumes that it has been already verified that notebook exists.

        Args:
            instance: notebook to delete
        """

        exists = self._instance_exists(instance)
        if exists:
            logger.user_info(f"Deleting {self.instance_type} {instance.name} ...")
            deleted = self._delete_instance_client(instance=instance)
            deleted.result()
            logger.user_success(f"Deleted {self.instance_type} {instance.name}")
        else:
            logger.user_error(
                f"{self.instance_type} with name {instance.name} was not found in location {self.workbench_location(instance)}",
            )
            typer.Exit(1)

    @abstractmethod
    def _delete_instance_client(self, instance: T) -> Operation:
        """
        Actually delete the instance from Vertex AI.

        Args:
            instance: Workbench instance to delete.

        Returns:
            operation: Operation for the deletion.
        """

    @abstractmethod
    def _create_instance_client(self, request: CreateRequest) -> Operation:
        """
        Actually create the instance in Vertex AI.

        Args:
            request: Request for creation

        Returns:
            operation: Operation for the creation.
        """

    def _validate_jupyterlab_state(self, instance_id: str, state: int) -> bool:
        """
        Validate if the given notebook instance is in given state.

        Args:
            instance_id: Full notebook instance id
            state: Notebook state (ACTIVE, PENDING,...)

        Returns:
            True if desired state, False otherwise
        """
        try:
            instance_info = self._client_get_instance(instance_id)
        except exceptions.NotFound:
            raise exceptions.NotFound(
                f"{self.instance_type} {instance_id} was not found."
            ) from None
        return instance_info.state == state

    @abstractmethod
    def _client_get_instance(self, instance_id: str) -> Instances:
        """
        Gets instance by id.

        Args:
            instance_id:

        Returns:
            instance: the instance
        """

    @abstractmethod
    def _get_jupyterlab_link(self, instance_id: str) -> str:
        """
        Get a link to jupyterlab proxy based on given notebook instance id.
        Args:
            instance_id: full notebook instance id

        Returns:
            proxy_uri: link to jupyterlab
        """
