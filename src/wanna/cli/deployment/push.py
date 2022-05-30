import json
from typing import Callable, List, Optional, Tuple, TypeVar

from smart_open import open

from wanna.cli.deployment.models import ContainerArtifact, JsonArtifact, PathArtifact, PushMode, PushTask
from wanna.cli.docker.service import DockerService
from wanna.cli.utils.spinners import Spinner

Manifest = TypeVar("Manifest")
PushResult = List[Tuple[Optional[List[ContainerArtifact]], Optional[List[PathArtifact]], Optional[List[JsonArtifact]]]]


def push(
    docker_service: DockerService,
    manifests: List[Manifest],
    packager: Callable[[List[Manifest], str, bool], List[PushTask]],
    version: str,
    local: bool = False,
    mode: PushMode = PushMode.all,
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

    push_tasks = packager(manifests, version, local)

    results: PushResult = []

    for push_task in push_tasks:
        if mode == PushMode.all:
            push_containers(container_artifacts=push_task.container_artifacts)
            push_manifests(manifest_artifacts=push_task.manifest_artifacts)
            push_json(artifacts=push_task.json_artifacts)
            results.append((push_task.container_artifacts, push_task.manifest_artifacts, push_task.json_artifacts))
        elif mode == PushMode.containers:
            push_containers(container_artifacts=push_task.container_artifacts)
            results.append((push_task.container_artifacts, None, None))
        elif mode == PushMode.manifests:
            push_manifests(manifest_artifacts=push_task.manifest_artifacts)
            push_json(artifacts=push_task.json_artifacts)
            results.append(
                (
                    None,
                    push_task.manifest_artifacts,
                    push_task.json_artifacts,
                )
            )

    return results
