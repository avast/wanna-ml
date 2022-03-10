import abc
from pathlib import Path
from typing import List

from wanna.cli.docker.service import DockerService
from wanna.cli.gcloud.service import GCloudService, GCPConfig
from wanna.cli.plugins.job.models import JobConfig


class JobService(abc.ABC):
    def __init__(
        self,
        version: str,
        build_dir: str,
        project_dir: Path,
        job_configs: List[JobConfig],
        gcp_config: GCPConfig,
        docker_service: DockerService,
    ) -> None:
        self.gcloud = GCloudService(gcp_config)
        self.job_configs = job_configs
        self.version = version
        self.docker_service = docker_service
        self.project_dir = project_dir
        self.build_dir = build_dir
        self.gcp_config = gcp_config

    def create(self):
        for job_config in self.job_configs:
            docker_build_dir = self.build_dir / job_config.name
            docker_build_dir.mkdir(parents=True, exist_ok=True)
            self.docker_service.build(
                docker_build=job_config.docker,
                image_name=f"{self.gcp_config.project_id}/{job_config.name}",
                project_dir=self.project_dir,
                version=self.version,
                build_args=None,
                platforms=None,
                ssh=None,
            )

        # 1. save yaml config
        # 2. snakify_job title
