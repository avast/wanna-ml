from pathlib import Path
from typing import List, Type, Dict
from abc import ABCMeta, abstractmethod
import typer

from wanna.cli.plugins.base.models import BaseInstanceModel, WannaProjectModel
from wanna.cli.utils import loaders
from wanna.cli.utils.gcp.models import GCPSettingsModel
from wanna.cli.utils.spinners import Spinner


class BaseService:
    """
    This is a base service and every other service (notebooks, jobs, pipelines,...)
    should build on top of this. It implements some basic function (create, delete)
    and utils for loading the wanna config.

    Args:
        instance_type: what are you working with (notebook, job, tensorboard) - used mainly in logging
        wanna_config_section: section of wanna-ml yaml config to read
        instance_model: pydantic instance model
    """

    def __init__(
        self,
        instance_type: str,
        wanna_config_section: str,
        instance_model: Type[BaseInstanceModel],
    ):
        __metaclass__ = ABCMeta
        self.wanna_config_path: Path
        self.wanna_config_section = wanna_config_section
        self.wanna_project: WannaProjectModel
        self.gcp_settings: GCPSettingsModel
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
                typer.echo(
                    f"{self.instance_type} with name {instance.name} was not found in zone {instance.zone}"
                )

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

    def load_config_from_yaml(self, wanna_config_path: Path) -> None:
        """
        Load the yaml file from wanna_config_path and parses the information to the models.
        This also includes the data validation.

        Args:
            wanna_config_path: path to the wanna-ml yaml file
        """

        with Spinner(text="Reading and validating yaml config"):
            self.wanna_config_path = wanna_config_path
            with open(self.wanna_config_path) as file:
                # Load workflow file
                wanna_dict = loaders.load_yaml(file, Path("."))
            self.wanna_project = WannaProjectModel.parse_obj(
                wanna_dict.get("wanna_project")
            )
            self.gcp_settings = GCPSettingsModel.parse_obj(
                wanna_dict.get("gcp_settings")
            )
            default_labels = self._generate_default_labels()

            for instance_dict in wanna_dict.get(self.wanna_config_section):
                instance = self.InstanceModel.parse_obj(
                    self._enrich_instance_info_with_gcp_settings_dict(instance_dict)
                )
                instance = self._add_labels(instance, default_labels)
                self.instances.append(instance)

    def _enrich_instance_info_with_gcp_settings_dict(self, instance_dict: dict) -> dict:
        """
        The dictionary instance_dict is updated with values from gcp_settings. This allows you to set values such as
        project_id and zone only on the wanna-ml config level but also give you the freedom to set separately for each
        notebook, jobs, etc. The values as at the instance level take precedence over general wanna-ml settings.

        Args:
            instance_dict: dict with values from wanna-ml config from one instance (one job, one notebook)

        Returns:
            dict: enriched with general gcp_settings if those information was not set on instance level

        """
        instance_info = self.gcp_settings.dict().copy()
        instance_info.update(instance_dict)
        return instance_info

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
                typer.echo(
                    f"No {self.instance_type} can be parsed from your wanna-ml yaml config."
                )
        else:
            instances = [nb for nb in self.instances if nb.name == instance_name]
        if not instances:
            typer.echo(
                f"{self.instance_type} with name {instance_name} not found in your wanna-ml yaml config."
            )
        return instances

    @staticmethod
    def _add_labels(
        instance: BaseInstanceModel, new_labels: Dict[str, str]
    ) -> BaseInstanceModel:
        """
        Add new labels to the instance model.
        Args:
            instance: BaseInstanceModel
            new_labels: new labels to be added

        Returns:
            new_instance: BaseInstanceModel with added labels
        """
        labels = instance.labels or {}
        labels.update(new_labels)
        instance.labels = labels
        return instance

    def _generate_default_labels(self) -> Dict[str, str]:
        """
        Get the default labels (GCP labels) that will be used with all instances.

        Returns:
            default labels
        """
        return {
            "wanna_project": self.wanna_project.name,
            "wanna_project_version": str(self.wanna_project.version),
            "wanna_project_author": self.wanna_project.author.partition("@")[0].replace(
                ".", "_"
            ),
        }
