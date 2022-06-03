import json
from typing import List, Tuple, TypeVar

from wanna.cli.deployment.models import ContainerArtifact, JsonArtifact, PathArtifact, PushTask
from wanna.cli.docker.service import DockerService
from wanna.cli.utils.io import open
from wanna.cli.utils.spinners import Spinner

Manifest = TypeVar("Manifest")
PushResult = List[Tuple[List[ContainerArtifact], List[PathArtifact], List[JsonArtifact]]]


def push(
    docker_service: DockerService,
    push_tasks: List[PushTask],
) -> PushResult:
    def push_containers(container_artifacts: List[ContainerArtifact]):
        for artifact in container_artifacts:
            with Spinner(text=f"Pushing {artifact.title.lower()} to {artifact.tags}"):
                docker_service.push_image(artifact.tags)

    def push_manifests(manifest_artifacts: List[PathArtifact]):
        for artifact in manifest_artifacts:
            with Spinner(text=f"Pushing {artifact.title.lower()} to {artifact.destination}"):
                with open(artifact.source, "r") as fin:
                    with open(artifact.destination, "w") as fout:
                        fout.write(fin.read())

    def push_json(artifacts: List[JsonArtifact]):
        for artifact in artifacts:
            with Spinner(text=f"Pushing {artifact.title.lower()} to {artifact.destination}"):
                with open(artifact.destination, "w") as fout:
                    fout.write(json.dumps(artifact.json_body))

    results: PushResult = []

    for push_task in push_tasks:

        push_containers(container_artifacts=push_task.container_artifacts)
        push_manifests(manifest_artifacts=push_task.manifest_artifacts)
        push_json(artifacts=push_task.json_artifacts)
        results.append((push_task.container_artifacts, push_task.manifest_artifacts, push_task.json_artifacts))

    return results
