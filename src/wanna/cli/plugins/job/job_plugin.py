import pathlib
from pathlib import Path

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
                self.create,
                self.stop,
            ]
        )

    @staticmethod
    def create(
        file: Path = file_option,
        profile_name: str = profile_option,
        instance_name: str = instance_name_option("job", "create"),
        sync: bool = True,
    ) -> None:
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        job_service = JobService(config=config, workdir=workdir)
        job_service.create(instance_name, sync=sync)

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
