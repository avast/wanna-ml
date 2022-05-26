import pathlib
from pathlib import Path

import typer

from wanna.cli.deployment.models import PushMode
from wanna.cli.plugins.base.base_plugin import BasePlugin
from wanna.cli.plugins.base.common_options import (
    instance_name_option,
    profile_name_option,
    push_mode_option,
    wanna_file_option,
)
from wanna.cli.plugins.job.service import JobService
from wanna.cli.utils.config_loader import load_config_from_yaml


class JobPlugin(BasePlugin):
    def __init__(self) -> None:
        super().__init__()
        self.register_many(
            [
                self.build,
                self.push,
                self.run,
                self.run_manifest,
                self.stop,
            ]
        )

    @staticmethod
    def build(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("job", "build"),
    ) -> None:
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        job_service = JobService(config=config, workdir=workdir)
        job_service.build(instance_name)

    @staticmethod
    def push(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        version: str = typer.Option(..., "--version", "-v", help="Job version"),
        instance_name: str = instance_name_option("job", "push"),
        mode: PushMode = push_mode_option,
    ) -> None:
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        job_service = JobService(config=config, workdir=workdir, version=version)
        jobs = job_service.build(instance_name)
        job_service.push(jobs, mode=mode)

    @staticmethod
    def run(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        version: str = typer.Option(..., "--version", "-v", help="Job version"),
        instance_name: str = instance_name_option("job", "run"),
        sync: bool = typer.Option(False, "--sync", "-s", help="Runs the job in sync mode"),
    ) -> None:
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        job_service = JobService(config=config, workdir=workdir, version=version)
        jobs = job_service.build(instance_name)
        manifest_paths, _ = job_service.push(jobs, local=True)
        JobService.run(manifest_paths, sync=sync)

    @staticmethod
    def run_manifest(
        manifest: str = typer.Option(None, "--manifest", "-v", help="Job deployment manifest"),
        sync: bool = typer.Option(False, "--sync", "-s", help="Runs the pipeline in sync mode"),
    ) -> None:
        JobService.run([manifest], sync=sync)

    @staticmethod
    def stop(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("job", "stop"),
    ) -> None:
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        job_service = JobService(config=config, workdir=workdir)
        job_service.stop(instance_name)
