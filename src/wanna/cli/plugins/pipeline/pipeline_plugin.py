import pathlib
from pathlib import Path
from typing import Optional

import typer
from google.cloud import aiplatform

from wanna.cli.plugins.base.base_plugin import BasePlugin
from wanna.cli.plugins.base.common_options import instance_name_option, profile_name_option, wanna_file_option
from wanna.cli.plugins.pipeline.service import PipelineService
from wanna.cli.utils.config_loader import load_config_from_yaml


class PipelinePlugin(BasePlugin):
    def __init__(self) -> None:
        super().__init__()
        self.register_many(
            [
                self.build,
                self.push,
                self.deploy,
                self.run,
            ]
        )

    @staticmethod
    def build(
        version: str = typer.Option("dev", "--version", "-v", help="Pipeline version"),
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("pipeline", "compile"),
    ) -> None:
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent
        pipeline_service = PipelineService(config=config, workdir=workdir, version=version)
        pipeline_service.build(instance_name)

    @staticmethod
    def push(
        version: str = typer.Option(..., "--version", "-v", help="Pipeline version"),
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("pipeline", "push"),
    ) -> None:
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent
        pipeline_service = PipelineService(config=config, workdir=workdir, version=version)
        pipelines = pipeline_service.build(instance_name)
        pipeline_service.push(pipelines, version)

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
        pipeline_service.deploy(instance_name, version, env)

    @staticmethod
    def run(
        version: str = typer.Option("dev", "--version", "-v", help="Pipeline version"),
        manifest: Optional[str] = typer.Option(
            None, "--manifest", "-m", help="Path to the wanna-manifest.json configuration"
        ),
        params: Path = typer.Option("params.yaml", "--params", "-p", help="Path to the params file in yaml format"),
        sync: bool = typer.Option(False, "--sync", "-s", help="Runs the pipeline in sync mode"),
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("pipeline", "run"),
    ) -> None:
        if file:
            config = load_config_from_yaml(file, gcp_profile_name=profile_name)
            aiplatform.init(project=config.gcp_profile.project_id, location=config.gcp_profile.region)
            workdir = pathlib.Path(file).parent
            pipeline_service = PipelineService(config=config, workdir=workdir, version=version)
            pipelines = pipeline_service.build(instance_name)
            manifests = pipeline_service.push(pipelines, version, local=True)
            manifest_paths = [str(wanna_manifest) for wanna_manifest, _ in manifests]
            PipelineService.run(manifest_paths, extra_params_path=params, sync=sync)
        elif manifest:
            PipelineService.run([manifest], extra_params_path=params, sync=sync)
        else:
            typer.echo(message="wanna pipeline run expects --file or --manifest", err=True)
            exit(1)
