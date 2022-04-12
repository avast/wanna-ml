import pathlib
from pathlib import Path
from typing import Optional

import typer

from wanna.cli.plugins.base.base_plugin import BasePlugin
from wanna.cli.plugins.base.common_options import wanna_file_option, instance_name_option, profile_option
from wanna.cli.plugins.job.service import JobService
from wanna.cli.utils.config_loader import load_config_from_yaml, load_gcp_profile


class JobPlugin(BasePlugin):
    def __init__(self) -> None:
        super().__init__()
        self.register_many(
            [
                self.build,
                self.push,
                self.stop,
                self.run_manifest,
                self.run,
            ]
        )


    @staticmethod
    def build(
        file: Path = wanna_file_option,
        profile_name: str = profile_option,
        version: str = typer.Option("dev", "--version", "-v", help="Pipeline version"),
        instance_name: str = instance_name_option("job", "build"),
    ) -> None:
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        job_service = JobService(config=config, workdir=workdir, version=version)
        job_service.build(instance_name)

    @staticmethod
    def push(
        file: Path = wanna_file_option,
        profile_name: str = profile_option,
        version: str = typer.Option(..., "--version", "-v", help="Pipeline version"),
        instance_name: str = instance_name_option("job", "push"),
    ) -> None:
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        job_service = JobService(config=config, workdir=workdir, version=version)
        jobs = job_service.build(instance_name)
        job_service.push(jobs)

    @staticmethod
    def run(
        file: Path = wanna_file_option,
        profile_name: str = profile_option,
        version: str = typer.Option(..., "--version", "-v", help="Job version"),
        instance_name: str = instance_name_option("job", "run"),
        sync: bool = typer.Option(False, "--sync", "-s", help="Runs the pipeline in sync mode"),
    ) -> None:
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        job_service = JobService(config=config, workdir=workdir, version=version)
        jobs = job_service.build(instance_name)
        manifests = job_service.push(jobs, local=True)
        JobService.run(manifests, gcp_profile=config.gcp_profile, sync=sync)

    @staticmethod
    def run_manifest(
        profile_name: str = profile_option,
        profiles_file: Optional[str] = typer.Option(None, "--profiles", "-pp", help="Path to GCP profiles yaml"),
        manifest: Optional[str] = typer.Option(None, "--manifest", "-v", help="Job deployment manifest"),
        sync: bool = typer.Option(False, "--sync", "-s", help="Runs the pipeline in sync mode"),
    ) -> None:
        gcp_profile = load_gcp_profile(profile_name=profile_name, wanna_dict={}, file_path=profiles_file)
        JobService.run([manifest], gcp_profile=gcp_profile, sync=sync)

    @staticmethod
    def stop(
        file: Path = wanna_file_option,
        profile_name: str = profile_option,
        instance_name: str = instance_name_option("job", "stop"),
    ) -> None:
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        job_service = JobService(config=config, workdir=workdir)
        job_service.stop(instance_name)
