from abc import ABC
from threading import Thread
from typing import Generic, List, Optional, Tuple, TypeVar

import typer

from wanna.core.deployment.models import PushMode
from wanna.core.loggers.wanna_logger import get_logger
from wanna.core.models.base_instance import BaseInstanceModel
from wanna.core.utils.gcp import convert_project_id_to_project_number, get_network_info

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseInstanceModel)


class BaseService(ABC, Generic[T]):
    """
    This is a base service and every other service (notebooks, jobs, pipelines,...)
    should build on top of this. It implements some basic function (create, delete)
    and utils for loading the wanna config.

    Args:
        instance_type: what are you working with (notebook, job, tensorboard) - used mainly in logging
        instance_model: pydantic instance model
    """

    def __init__(
        self,
        instance_type: str,
    ):
        self.instances: List[T] = []
        self.instance_type = instance_type

    def create(self, instance_name: str, **kwargs) -> None:
        """
        Create an instance with name "name" based on wanna-ml config.

        Args:
            instance_name: The name of the only instance from wanna-ml config that should be created.
                  Set to "all" to create everything from wanna-ml yaml configuration.
        """
        instances = self._filter_instances_by_name(instance_name)

        for instance in instances:
            self._create_one_instance(instance, **kwargs)

    def delete(self, instance_name: str) -> None:
        """
        Delete an instance with name "name" based on wanna-ml config if exists on GCP.

        Args:
            instance_name: The name of the only instance from wanna-ml config that should be deleted.
                  Set to "all" to create all from configuration.
        """
        instances = self._filter_instances_by_name(instance_name)

        for instance in instances:
            self._delete_one_instance(instance)

    def stop(self, instance_name: str) -> None:
        """
        Stop an instance with name "name" based on wanna-ml config.

        Args:
            instance_name: The name of the only instance from wanna-ml config that should be stopped.
                  Set to "all" to delete everything from wanna-ml yaml configuration for this resource.
        """
        instances = self._filter_instances_by_name(instance_name)

        for instance in instances:
            self._stop_one_instance(instance)

    def _delete_one_instance(self, instance: T) -> None:
        """
        Abstract class. Should delete one instance based on one model (eg. delete one notebook).
        """
        raise NotImplementedError

    def _create_one_instance(self, instance: T, **kwargs) -> None:
        """
        Abstract class. Should create one instance based on one model (eg. create one notebook).
        """
        raise NotImplementedError

    def _stop_one_instance(self, instance: T) -> None:
        """
        Abstract class. Should stop one instance based on one model (eg. stop one job).
        """
        raise NotImplementedError

    def _filter_instances_by_name(self, instance_name: str) -> List[T]:
        """
        From self.instances filter only the instances with name instance_name.

        Args:
            instance_name: Name of the instance to return. Set to "all" to return all instances.

        Returns:
            instances

        """
        if instance_name == "all":
            instances = self.instances
            if not instances:
                logger.user_error(
                    f"No {self.instance_type} can be parsed from your wanna-ml yaml config."
                )
                exit(1)
        else:
            instances = [nb for nb in self.instances if nb.name == instance_name]
        if not instances:
            logger.user_error(
                f"{self.instance_type} with name {instance_name} not found in your wanna-ml yaml config.",
            )
            exit(1)

        return instances

    def report(
        self,
        instance_name: str,
        wanna_project: str,
        wanna_resource: str,
        gcp_project: str,
        billing_id: Optional[str],
        organization_id: Optional[str],
    ) -> None:
        """
        Displays a link to the Google Cloud cost report
        """
        if not billing_id or not organization_id:
            logger.user_error(
                "Billing and Organization IDs are needed. Please provide them in wanna.yaml"
            )
            return None

        base_url = f"https://console.cloud.google.com/billing/{billing_id}/reports;projects={gcp_project}"

        if instance_name == "all":
            labels = (
                f";labels=wanna_project:{wanna_project},wanna_resource:{wanna_resource}"
            )
        elif instance_name not in [nb.name for nb in self.instances]:
            logger.user_error(
                f"{self.instance_type} with name {instance_name} not found in your wanna-ml yaml config.",
            )
            return None
        else:
            labels = f";labels=wanna_project:{wanna_project},wanna_resource:{wanna_resource},wanna_name:{instance_name}"

        link = base_url + labels + f"?organizationId={organization_id}"
        logger.user_info(f"Here is a link to your {wanna_resource} cost report:")
        logger.user_success(f"{link}")

    def _get_resource_network(
        self,
        project_id: str,
        push_mode: PushMode,
        resource_network: Optional[str],
        fallback_project_network: Optional[str],
        use_project_number: bool = True,
    ):
        resource_network = (
            resource_network if resource_network else fallback_project_network
        )
        if resource_network:
            result = get_network_info(resource_network)
            if result:
                # long format network found
                project_id, resource_network = result

            # In certain scenarios we can't build on GCP and have no access to GCP from within Avast build infra
            if push_mode.can_push_gcp_resources():
                if not project_id.isdigit() and use_project_number:
                    project_id = convert_project_id_to_project_number(project_id)

            return f"projects/{project_id}/global/networks/{resource_network}"
        else:
            return None

    def _get_resource_subnet(
        self, network: Optional[str], subnet: Optional[str], region: Optional[str]
    ):
        if subnet:
            # Assumes the full qualified path was provided in config
            if "/" in subnet:
                return subnet
            else:
                # Get the project id from the provided network and pass it to subnet
                if network:
                    network_project_parts = network.split("/")
                    if len(network_project_parts) >= 2:
                        network_project_id = network_project_parts[1]
                    else:
                        network_project_id = network
                return f"projects/{network_project_id}/regions/{region}/subnetworks/{subnet}"
        else:
            return None

    def _return_diff(self) -> Tuple[List[T], List[T]]:
        """
        Abstract class.
        """
        raise NotImplementedError

    def sync(self, force: bool, push_mode: PushMode = PushMode.all) -> None:
        """
        1. Reads current instances where label is defined per field wanna_project.name in wanna.yaml
        2. Does a diff between what is on GCP and what is on yaml
        3. Delete the ones in GCP that are not in wanna.yaml
        4. Create the ones defined in yaml and missing in GCP
        """
        (
            to_be_deleted,
            to_be_created,
        ) = self._return_diff()  # pylint: disable=assignment-from-no-return

        if to_be_deleted:
            to_be_deleted_str = "\n".join(["- " + item.name for item in to_be_deleted])
            logger.user_info(
                f"{self.instance_type.capitalize()}s to be deleted:\n{to_be_deleted_str}"
            )
            should_delete = (
                True
                if force
                else typer.confirm("Are you sure you want to delete them?")
            )
            if should_delete:
                for notebook in to_be_deleted:
                    t = Thread(target=self._delete_one_instance, args=(notebook,))
                    t.start()

        if to_be_created:
            to_be_created_str = "\n".join(["- " + item.name for item in to_be_created])
            logger.user_info(
                f"{self.instance_type.capitalize()}s to be created:\n{to_be_created_str}"
            )
            should_create = (
                True
                if force
                else typer.confirm("Are you sure you want to create them?")
            )
            if should_create:
                for notebook in to_be_created:
                    t = Thread(
                        target=self._create_one_instance,
                        args=(notebook,),
                        kwargs={push_mode: push_mode},
                    )
                    t.start()

        logger.user_info(
            f"{self.instance_type.capitalize()}s on GCP are in sync with wanna.yaml"
        )
