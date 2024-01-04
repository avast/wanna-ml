import json
from typing import Callable, List

from wanna.core.deployment.io import IOMixin
from wanna.core.deployment.models import (
    ContainerArtifact,
    JsonArtifact,
    PathArtifact,
    PushResult,
    PushTask,
)
from wanna.core.loggers.wanna_logger import get_logger

logger = get_logger(__name__)


class ArtifactsPushMixin(IOMixin):
    def push_artifacts(
        self, docker_pusher: Callable[[List[str]], None], push_tasks: List[PushTask]
    ) -> PushResult:
        def push_containers(container_artifacts: List[ContainerArtifact]):
            for artifact in container_artifacts:
                with logger.user_spinner(
                    f"Pushing {artifact.name.lower()} to {artifact.tags}"
                ):
                    docker_pusher(artifact.tags)

        def push_manifests(manifest_artifacts: List[PathArtifact]):
            for artifact in manifest_artifacts:
                with logger.user_spinner(
                    f"Pushing {artifact.name.lower()} to {artifact.destination}"
                ):
                    self.upload_file(artifact.source, artifact.destination)

        def push_json(artifacts: List[JsonArtifact]):
            for artifact in artifacts:
                with logger.user_spinner(
                    f"Pushing {artifact.name.lower()} to {artifact.destination}"
                ):
                    self.write(artifact.destination, json.dumps(artifact.json_body))

        results: PushResult = []

        for push_task in push_tasks:
            push_containers(container_artifacts=push_task.container_artifacts)
            push_manifests(manifest_artifacts=push_task.manifest_artifacts)
            push_json(artifacts=push_task.json_artifacts)
            results.append(
                (
                    push_task.container_artifacts,
                    push_task.manifest_artifacts,
                    push_task.json_artifacts,
                )
            )

        return results
