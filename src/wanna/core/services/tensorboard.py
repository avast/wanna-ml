import logging
from typing import List, Union, cast

import typer
from google.cloud import aiplatform
from google.cloud.aiplatform.tensorboard.tensorboard_resource import (
    Tensorboard,
    TensorboardExperiment,
)
from treelib import Tree

from wanna.core.loggers.wanna_logger import get_logger
from wanna.core.models.tensorboard import TensorboardModel
from wanna.core.models.wanna_config import WannaConfigModel
from wanna.core.services.base import BaseService

logger_gcs = logging.getLogger("google.cloud")
logger_gcs.setLevel(logging.ERROR)

logger = get_logger(__name__)


class TensorboardService(BaseService[TensorboardModel]):
    def __init__(self, config: WannaConfigModel):
        super().__init__(
            instance_type="tensorboard",
        )
        self.config = config
        self.instances = config.tensorboards

    def _delete_one_instance(self, instance: TensorboardModel) -> None:
        """
        Deletes one running Tensorboard Instance.

        Args:
            instance:
        """
        tensorboard = self._find_existing_tensorboard_by_model(instance)
        if not tensorboard:
            logger.user_info(
                f"Tensorboard {instance.name} does not exist, nothing to delete."
            )
        else:
            with logger.user_spinner(f"Deleting Tensorboard {instance.name}"):
                aiplatform.Tensorboard(
                    tensorboard_name=tensorboard.resource_name
                ).delete()

    def _create_one_instance(
        self, instance: TensorboardModel, **kwargs  # noqa: ARG002
    ) -> None:
        """
        Creates one Tensorboard instance based on pydantic model.

        Args:
            instance:

        Returns:

        """
        if self._instance_exists(instance):
            existing_instance = self._find_existing_tensorboard_by_model(instance)
            if existing_instance:
                logger.user_info(
                    f"Tensorboard {instance.name} already exists and is running at {existing_instance.resource_name}"
                )
                should_recreate = typer.confirm(
                    "Are you sure you want to delete it and start a new?"
                )
                if should_recreate:
                    self._delete_one_instance(instance)
                else:
                    return
        with logger.user_spinner(f"Creating Tensorboard {instance.name}"):
            aiplatform.Tensorboard.create(
                display_name=instance.name,
                description=instance.description,
                labels=instance.labels,
                project=instance.project_id,
                location=instance.region,
            )

        created = self._find_existing_tensorboard_by_model(instance)
        if created:
            logger.user_info(
                f"Tensorboard {instance.name} is running at {created.resource_name}"
            )

    def _find_existing_tensorboard_by_model(
        self, instance: TensorboardModel
    ) -> Union[Tensorboard, None]:
        """
        Given pydantic tensorboard model, find the actual running tensorboard instance on GCP.

        Args:
            instance:

        Returns:
            Tensorboard or None if not found
        """
        for running_tensorboard in self._list_running_instances(
            instance.project_id, instance.region
        ):
            if running_tensorboard.display_name == instance.name:
                return running_tensorboard
        return None

    def _instance_exists(self, instance: TensorboardModel) -> bool:
        """
        Find if there is any running tensorboard instance on GCP
        that corresponds to pydantic TensorboardModel.
        Args:
            instance:

        Returns:
            True is we find a match, False otherwise
        """
        found = self._find_existing_tensorboard_by_model(instance)
        return found is not None

    @staticmethod
    def _list_running_instances(project_id: str, region: str) -> List["Tensorboard"]:
        """
        List all tensorboards with given project_id and region

        Args:
            project_id: GCP project ID
            region: GCP region

        Returns:
            instances: List of the tensorboard instances

        """
        instances = cast(
            List[Tensorboard],
            aiplatform.Tensorboard.list(project=project_id, location=region),
        )
        return instances

    def _find_tensorboard_model_by_name(self, tb_name: str) -> TensorboardModel:
        """
        Finds tensorboard model when given the name of the model.
        Args:
            tb_name: name of the tensorboard model

        Returns:
            TensorboardModel
        """
        matched_tb_models: List[TensorboardModel] = list(
            filter(lambda i: i.name.strip() == tb_name.strip(), self.instances)
        )

        if len(matched_tb_models) == 0:
            raise ValueError(f"No tensorboard model with name {tb_name} found")
        elif len(matched_tb_models) > 1:
            raise ValueError(
                f"Multiple tensorboard models with name {tb_name} found, please use unique names"
            )
        else:
            return matched_tb_models[0]

    def get_or_create_tensorboard_instance_by_name(self, tensorboard_name: str) -> str:
        """
        Given the name of the tensorboard model, it will either return the full resource name of
        existing tensborbord (eg. projects/966197297054/locations/europe-west4/tensorboards/498421815010394112)
        or create a tensorboard with given name if it doesnt exist yet and then return the full path
        Args:
            tensorboard_name:

        Returns:
            full tensorboard resource name
        """
        tb_model = self._find_tensorboard_model_by_name(tb_name=tensorboard_name)
        tb_existing = self._find_existing_tensorboard_by_model(instance=tb_model)
        if not tb_existing:
            logger.user_info(
                f"Tensorboard with name {tb_model.name} in {tb_model.region} not found, creating it."
            )
            self._create_one_instance(tb_model)
            tb_existing = self._find_existing_tensorboard_by_model(instance=tb_model)
            if not tb_existing:
                raise ValueError("Error when creating Tensorboard instance")
        return tb_existing.resource_name

    @staticmethod
    def construct_tb_experiment_url_link(experiment: TensorboardExperiment) -> str:
        """
        Google API doesnt provide any support for getting a URL link to tensorboard experiment.
        Hence use this helper function to do it.
        Args:
            experiment:

        Returns:
            link to the experiment
        """
        return (
            f"https://{experiment.location}.tensorboard.googleusercontent.com/"
            f'experiment/{experiment.resource_name.replace("/", "+")}'
        )

    def _create_tensorboard_tree(
        self, region: str, filter_expr: str, show_url: bool
    ) -> Tree:
        """
        Create a tensorboard instance - tensorboard experiment - tensorboard run tree
        Args:
            region: gcp region
            filter_expr: gcp filter expression
            show_url: wheather to show url to experiments

        Returns:
            tree
        """
        tree = Tree()
        project_id = self.config.gcp_profile.project_id
        root_tag = f"{project_id} / {region}"
        tree.create_node(tag=root_tag, identifier=root_tag)

        tensorboards = aiplatform.Tensorboard.list(
            project=project_id, location=region, filter=filter_expr
        )
        for tensorboard in tensorboards:
            tag = f"Tensorboard: {tensorboard.display_name}"
            tree.create_node(
                tag=tag,
                identifier=tensorboard.resource_name,
                parent=root_tag,
                data=tensorboard,
            )
            experiments = aiplatform.TensorboardExperiment.list(
                tensorboard.resource_name
            )
            for experiment in experiments:
                tag = f"Experiment: {experiment.display_name or experiment.name}"
                if show_url:
                    tag += " " + self.construct_tb_experiment_url_link(experiment)
                tree.create_node(
                    tag=tag,
                    identifier=experiment.resource_name,
                    parent=tensorboard.resource_name,
                    data=experiment,
                )
                runs = aiplatform.TensorboardRun.list(
                    tensorboard_experiment_name=experiment.resource_name
                )
                for run in runs:
                    tag = f"Run: {run.display_name or run.name}"
                    tree.create_node(
                        tag=tag,
                        identifier=run.resource_name,
                        parent=experiment.resource_name,
                        data=run,
                    )
        return tree

    def list_tensorboards_in_tree(
        self, region: str, filter_expr: str, show_url: bool
    ) -> None:
        with logger.user_spinner("Creating Tensorboard tree"):
            tree = self._create_tensorboard_tree(
                region=region, filter_expr=filter_expr, show_url=show_url
            )
        tree.show()
