from abc import ABC
from typing import Generic, List, TypeVar

import typer

from wanna.core.models.base_instance import BaseInstanceModel

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
                typer.secho(
                    f"No {self.instance_type} can be parsed from your wanna-ml yaml config.", fg=typer.colors.RED
                )
        else:
            instances = [nb for nb in self.instances if nb.name == instance_name]
        if not instances:
            typer.secho(
                f"{self.instance_type} with name {instance_name} not found in your wanna-ml yaml config.",
                fg=typer.colors.RED,
            )

        return instances
