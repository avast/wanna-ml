from abc import ABC
from typing import Generic, List, TypeVar

from wanna.core.loggers.wanna_logger import get_logger
from wanna.core.models.base_instance import BaseInstanceModel

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
        ...

    def _create_one_instance(self, instance: T, **kwargs) -> None:
        """
        Abstract class. Should create one instance based on one model (eg. create one notebook).
        """
        ...

    def _stop_one_instance(self, instance: T) -> None:
        """
        Abstract class. Should stop one instance based on one model (eg. stop one job).
        """
        ...

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
                logger.user_error(f"No {self.instance_type} can be parsed from your wanna-ml yaml config.")
        else:
            instances = [nb for nb in self.instances if nb.name == instance_name]
        if not instances:
            logger.user_error(
                f"{self.instance_type} with name {instance_name} not found in your wanna-ml yaml config.",
            )

        return instances

    def report(self, instance_name: str, wanna_project: str, wanna_resource: str, gcp_project: str) -> None:
        """
        Sends a link to cost report
        Billing and Organization IDs are hard coded
        """
        base_url = f"https://console.cloud.google.com/billing/0141C8-E9DEB5-FDB1A3/reports;projects={gcp_project}"
        organization = "?organizationId=676993294933"

        if instance_name == "all":
            labels = f"labels=wanna_project:{wanna_project},wanna_resource:{wanna_resource}"
        elif instance_name not in [nb.name for nb in self.instances]:
            logger.user_error(
                f"{self.instance_type} with name {instance_name} not found in your wanna-ml yaml config.",
            )
            return
        else:
            labels = f"labels=wanna_project:{wanna_project},wanna_resource:{wanna_resource},wanna_name:{instance_name}"

        link = base_url + labels + organization
        logger.user_info(f"Here is a link to your {wanna_resource} cost report:")
        logger.user_success(f"{link}")
