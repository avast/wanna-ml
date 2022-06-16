import pathlib
from pathlib import Path

import typer

from wanna.cli.plugins.base_plugin import BasePlugin
from wanna.cli.plugins.common_options import (
    instance_name_option,
    profile_name_option,
    push_mode_option,
    wanna_file_option,
)
from wanna.core.deployment.models import PushMode
from wanna.core.services.pipeline import PipelineService
from wanna.core.utils.config_loader import load_config_from_yaml


class PipelinePlugin(BasePlugin):
    def __init__(self) -> None:
        super().__init__()
        self.register_many(
            [
                self.build,
                self.push,
                self.deploy,
                self.run,
                self.run_manifest,
                self.report,
            ]
        )

    @staticmethod
    def build(
        version: str = typer.Option("dev", "--version", "-v", help="Pipeline version"),
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("pipeline", "compile"),
        mode: PushMode = push_mode_option,
    ) -> None:
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent
        pipeline_service = PipelineService(config=config, workdir=workdir, version=version, push_mode=mode)
        pipeline_service.build(instance_name)

    @staticmethod
    def push(
        version: str = typer.Option(..., "--version", "-v", help="Pipeline version"),
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("pipeline", "push"),
        mode: PushMode = push_mode_option,
    ) -> None:
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent
        pipeline_service = PipelineService(config=config, workdir=workdir, version=version, push_mode=mode)
        manifests = pipeline_service.build(instance_name)
        pipeline_service.push(manifests)

    @staticmethod
    def deploy(
        version: str = typer.Option(..., "--version", "-v", help="Pipeline version"),
        env: str = typer.Option("local", "--env", "-e", help="Pipeline env"),
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("pipeline", "deploy"),
    ) -> None:
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent
        pipeline_service = PipelineService(config=config, workdir=workdir, version=version)
        pipeline_service.deploy(instance_name, env)

    @staticmethod
    def run(
        version: str = typer.Option("dev", "--version", "-v", help="Pipeline version"),
        params: Path = typer.Option("params.yaml", "--params", "-p", help="Path to the params file in yaml format"),
        sync: bool = typer.Option(False, "--sync", "-s", help="Runs the pipeline in sync mode"),
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("pipeline", "run"),
    ) -> None:
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent
        pipeline_service = PipelineService(config=config, workdir=workdir, version=version)
        manifests = pipeline_service.build(instance_name)
        pipeline_service.push(manifests, local=False)
        PipelineService.run([str(p) for p in manifests], extra_params=params, sync=sync)

    @staticmethod
    def run_manifest(
        manifest: str = typer.Option(None, "--manifest", "-v", help="Job deployment manifest"),
        params: Path = typer.Option("params.yaml", "--params", "-p", help="Path to the params file in yaml format"),
        sync: bool = typer.Option(False, "--sync", "-s", help="Runs the pipeline in sync mode"),
    ) -> None:
        PipelineService.run([manifest], extra_params=params, sync=sync)

    @staticmethod
    def report(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("managed_notebook", "report"),
    ) -> None:
        """
        Displays a link to the cost report per wanna_project and optionally per instance name
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent
        pipeline_service = PipelineService(config=config, workdir=workdir)
        pipeline_service.report(
            instance_name=instance_name,
            wanna_project=config.wanna_project.name,
            wanna_resource="pipeline",
            gcp_project=config.gcp_profile.project_id,
        )
