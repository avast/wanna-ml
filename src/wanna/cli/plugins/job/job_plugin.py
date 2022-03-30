from pathlib import Path

import typer

from wanna.cli.plugins.base.base_plugin import BasePlugin
from wanna.cli.plugins.job.service import JobService
from wanna.cli.utils.config_loader import load_config_from_yaml


class JobPlugin(BasePlugin):
    def __init__(self) -> None:
        super(JobPlugin, self).__init__()
        self.secret = "some value"
        self.register_many(
            [
                self.create,
                self.stop,
            ]
        )

        # self.app.add_typer(SubJobPlugin().app, name='sub-job-command')

    @staticmethod
    def create(
        file: Path = typer.Option("wanna.yaml", "--file", "-f", help="Path to the wanna-ml yaml configuration"),
        instance_name: str = typer.Option(
            "all",
            "--name",
            "-n",
            help="Specify only one job from your wanna-ml yaml configuration to create. "
            "Choose 'all' to create all jobs.",
        ),
        sync: bool = True,
    ) -> None:
        config = load_config_from_yaml(file)
        job_service = JobService(config=config)
        job_service.create(instance_name, sync=sync)

    @staticmethod
    def stop(
        file: Path = typer.Option("wanna.yaml", "--file", "-f", help="Path to the wanna-ml yaml configuration"),
        instance_name: str = typer.Option(
            "all",
            "--name",
            "-n",
            help="Specify only one job from your wanna-ml yaml configuration to create. "
            "Choose 'all' to create all jobs.",
        ),
    ) -> None:
        config = load_config_from_yaml(file)
        job_service = JobService(config=config)
        job_service.stop(instance_name)
