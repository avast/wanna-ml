from abc import ABC, abstractmethod
from typing import List, Type

import typer

from wanna.cli.models.base_instance import BaseInstanceModel


class BaseService(ABC):
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
        instance_model: Type[BaseInstanceModel],
    ):
        self.instances: List[BaseInstanceModel] = []
        self.instance_type = instance_type
        self.InstanceModel = instance_model

    def create(self, instance_name: str) -> None:
        """
        Create an instance with name "name" based on wanna-ml config.

        Args:
            instance_name: The name of the only instance from wanna-ml config that should be created.
                  Set to "all" to create everything from wanna-ml yaml configuration.
        """
        instances = self._filter_instances_by_name(instance_name)

        for instance in instances:
            self._create_one_instance(instance)

    def delete(self, instance_name: str) -> None:
        """
        Delete an instance with name "name" based on wanna-ml config if exists on GCP.

        Args:
            instance_name: The name of the only instance from wanna-ml config that should be deleted.
                  Set to "all" to create all from configuration.
        """
        instances = self._filter_instances_by_name(instance_name)

        for instance in instances:
            exists = self._instance_exists(instance)
            if exists:
                self._delete_one_instance(instance)
            else:
                typer.echo(f"{self.instance_type} with name {instance.name} was not found in zone {instance.zone}")

    @abstractmethod
    def _delete_one_instance(self, instance: BaseInstanceModel) -> None:
        """
        Abstract class. Should delete one instance based on one model (eg. delete one notebook).
        """
        ...

    @abstractmethod
    def _create_one_instance(self, instance: BaseInstanceModel) -> None:
        """
        Abstract class. Should create one instance based on one model (eg. create one notebook).
        """
        ...

    @abstractmethod
    def _instance_exists(self, instance: BaseInstanceModel) -> bool:
        """
        Abstract method to find it this instance already exists on GCP.

        Args:
            instance: instance to verify if it already exists

        Returns:
            True if found on GCP, False otherwise
        """
        ...

    def _filter_instances_by_name(self, instance_name: str) -> List[BaseInstanceModel]:
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
                typer.echo(f"No {self.instance_type} can be parsed from your wanna-ml yaml config.")
        else:
            instances = [nb for nb in self.instances if nb.name == instance_name]
        if not instances:
            typer.echo(f"{self.instance_type} with name {instance_name} not found in your wanna-ml yaml config.")
        return instances
