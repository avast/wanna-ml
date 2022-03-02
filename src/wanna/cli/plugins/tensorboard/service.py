import logging
from typing import List, Union
from wanna.cli.models.wanna_config import WannaConfigModel
import typer
from google.cloud import aiplatform
from google.cloud.aiplatform.tensorboard.tensorboard_resource import Tensorboard
from wanna.cli.plugins.base.service import BaseService
from wanna.cli.models.tensorboard import TensorboardModel
from wanna.cli.utils.spinners import Spinner

logger = logging.getLogger("google.cloud")
logger.setLevel(logging.ERROR)


class TensorboardService(BaseService):
    def __init__(self):
        super().__init__(
            instance_type="tensorboard",
            instance_model=TensorboardModel,
        )

    def load_config(self, config: WannaConfigModel):
        self.instances = config.tensorboards

    def _delete_one_instance(self, instance: TensorboardModel) -> None:
        """
        Deletes one running Tensorboard Instance.

        Args:
            instance:
        """
        tensorboard = self._find_tensorboard_by_display_name(instance)
        if not tensorboard:
            typer.echo(
                f"Tensorboard {instance.name} does not exist, nothing to delete."
            )
        else:
            with Spinner(text=f"Deleting Tensorboard {instance.name}"):
                aiplatform.Tensorboard(
                    tensorboard_name=tensorboard.resource_name
                ).delete()

    def _create_one_instance(self, instance: TensorboardModel) -> None:
        """
        Creates one Tensorboard instance based on pydantic model.

        Args:
            instance:

        Returns:

        """
        if self._instance_exists(instance):
            existing_instance = self._find_tensorboard_by_display_name(instance)
            typer.echo(
                f"Tensorboard {instance.name} already exists and is running at {existing_instance.resource_name}"
            )
            should_recreate = typer.confirm(
                "Are you sure you want to delete it and start a new?"
            )
            if should_recreate:
                self._delete_one_instance(instance)
            else:
                return
        with Spinner(text=f"Creating Tensorboard {instance.name}"):
            aiplatform.Tensorboard.create(
                display_name=instance.name,
                description=instance.description,
                labels=instance.labels,
                project=instance.project_id,
                location=instance.region,
            )
        created = self._find_tensorboard_by_display_name(instance)
        typer.echo(f"Tensorboard {instance.name} is running at {created.resource_name}")

    def _find_tensorboard_by_display_name(
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
        found = self._find_tensorboard_by_display_name(instance)
        return found is not None

    @staticmethod
    def _list_running_instances(project_id: str, region: str) -> List[Tensorboard]:
        """
        List all tensorboards with given project_id and region

        Args:
            project_id: GCP project ID
            region: GCP region

        Returns:
            instances: List of the tensorboard instances

        """
        instances = aiplatform.Tensorboard.list(project=project_id, location=region)
        return instances
