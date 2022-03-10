from pathlib import Path
from typing import Optional

import typer

from wanna.cli.docker.service import DockerService
from wanna.cli.plugins.base import BasePlugin
from wanna.cli.plugins.job.service import JobService
from wanna.cli.plugins.loader import load_wanna


class JobCommand(BasePlugin):
    def __init__(self) -> None:
        super(JobCommand, self).__init__()
        self.secret = "some value"
        self.register_many([self.create])

        # add some nesting with `sub-job-command` command.
        # self.app.add_typer(SubJobPlugin().app, name='sub-job-command')

    @staticmethod
    def create(
        ctx: typer.Context,
        version: str = typer.Argument("snapshot"),
        project_file: Path = typer.Argument(Path("wanna.yaml")),
        project_dir: Optional[Path] = None,
    ) -> None:

        if not project_dir:
            project_dir = project_file.parent

        build_dir = project_dir / "build"

        docker_repository = "eu.gcr.io"
        docker_service = DockerService(
            build_dir=build_dir, working_dir=project_dir, docker_repository=docker_repository
        )
        # version: str, working_dir: Path, project_dir: Path, job_configs: List[JobConfig], gcp_config: GCPConfig, docker_service: DockerService
        wanna = load_wanna(project_file=project_file, project_dir=project_dir)
        service = JobService(
            version=version,
            build_dir=build_dir,
            project_dir=project_dir,
            job_configs=wanna.jobs,
            gcp_config=wanna.gcp,
            docker_service=docker_service,
        )

        service.create()

        # version: str, working_dir: Path, project_dir: Path, job_configs: List[JobConfig], gcp_config: GCPConfig, docker_service: DockerService
        pass
