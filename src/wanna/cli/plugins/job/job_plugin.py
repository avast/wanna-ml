import pathlib
from pathlib import Path
import typer

from wanna.cli.plugins.base.base_plugin import BasePlugin
from wanna.cli.plugins.base.common_options import file_option, instance_name_option, profile_option
from wanna.cli.plugins.job.service import JobService
from wanna.cli.utils.config_loader import load_config_from_yaml


class JobPlugin(BasePlugin):
    def __init__(self) -> None:
        super().__init__()
        self.secret = "some value"
        self.register_many(
            [
                self.build,
                self.push,
                self.stop,
            ]
        )

        # self.app.add_typer(SubJobPlugin().app, name='sub-job-command')

    @staticmethod
    def build(
        file: Path = file_option,
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
        file: Path = file_option,
        profile_name: str = profile_option,
        version: str = typer.Option(..., "--version", "-v", help="Pipeline version"),
        instance_name: str = instance_name_option("job", "push"),
    ) -> None:
        config = load_config_from_yaml(file)
        workdir = pathlib.Path(file).parent.resolve()
        job_service = JobService(config=config, workdir=workdir, version=version)
        jobs = job_service.build(instance_name)
        job_service.push(jobs)

    @staticmethod
    def stop(
        file: Path = file_option,
        profile_name: str = profile_option,
        instance_name: str = instance_name_option("job", "stop"),
    ) -> None:
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        job_service = JobService(config=config, workdir=workdir)
        job_service.stop(instance_name)
