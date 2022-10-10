import pathlib
from pathlib import Path

import typer

from wanna.cli.plugins.base_plugin import BasePlugin
from wanna.cli.plugins.common_options import (
    instance_name_option,
    profile_name_option,
    push_mode_option,
    version_option,
    wanna_file_option,
)
from wanna.core.deployment.models import PushMode
from wanna.core.services.jobs import JobService
from wanna.core.utils.config_loader import load_config_from_yaml


class JobPlugin(BasePlugin):
    """
    Plugin for building and deploying training jobs.
    """

    def __init__(self) -> None:
        super().__init__()
        self.register_many(
            [
                self.build,
                self.push,
                self.run,
                self.run_manifest,
                self.stop,
                self.report,
            ]
        )

    @staticmethod
    def build(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("job", "build"),
    ) -> None:
        """
        Create a manifest based on the wanna-ml config that can be later pushed or run.
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        job_service = JobService(config=config, workdir=workdir)
        job_service.build(instance_name)

    @staticmethod
    def push(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        version: str = version_option(instance_type="job"),
        instance_name: str = instance_name_option("job", "push"),
        mode: PushMode = push_mode_option,
    ) -> None:
        """
        Build and push manifest to Cloud Storage.
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        job_service = JobService(config=config, workdir=workdir, version=version, push_mode=mode)
        manifests = job_service.build(instance_name)
        job_service.push(manifests)

    @staticmethod
    def run(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        version: str = version_option(instance_type="job"),
        instance_name: str = instance_name_option("job", "run"),
        hp_params: Path = typer.Option(None, "--hp-params", "-hp", help="Path to the params file in yaml format"),
        sync: bool = typer.Option(False, "--sync", "-s", help="Runs the job in sync mode"),
    ) -> None:
        """
        Run the job as specified in wanna-ml config. This command puts together build, push and run-manifest steps.
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        job_service = JobService(config=config, workdir=workdir, version=version)
        manifests = job_service.build(instance_name)
        job_service.push(manifests, local=False)
        JobService.run([str(p) for p in manifests], sync=sync, hp_params=hp_params)

    @staticmethod
    def run_manifest(
        manifest: str = typer.Option(None, "--manifest", "-v", help="Job deployment manifest"),
        hp_params: Path = typer.Option(None, "--hp-params", "-hp", help="Path to the params file in yaml format"),
        sync: bool = typer.Option(False, "--sync", "-s", help="Runs the pipeline in sync mode"),
    ) -> None:
        """
        Run the job as specified in the wanna-ml manifest.
        """
        JobService.run(manifests=[manifest], sync=sync, hp_params=hp_params)

    @staticmethod
    def stop(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("job", "stop"),
    ) -> None:
        """
        Stop a running job.
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        job_service = JobService(config=config, workdir=workdir)
        job_service.stop(instance_name)

    @staticmethod
    def report(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("job", "report"),
    ) -> None:
        """
        Displays a link to the cost report per wanna_project and optionally per job name.
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent.resolve()
        job_service = JobService(config=config, workdir=workdir)
        job_service.report(
            instance_name=instance_name,
            wanna_project=config.wanna_project.name,
            wanna_resource="job",
            gcp_project=config.gcp_profile.project_id,
            billing_id=config.wanna_project.billing_id,
            organization_id=config.wanna_project.organization_id,
        )
