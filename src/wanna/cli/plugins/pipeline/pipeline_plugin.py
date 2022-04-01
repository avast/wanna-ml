import pathlib
from pathlib import Path
from typing import Optional

import typer

from wanna.cli.plugins.base.base_plugin import BasePlugin
from wanna.cli.plugins.pipeline.service import PipelineService
from wanna.cli.utils.config_loader import load_config_from_yaml


class PipelinePlugin(BasePlugin):
    def __init__(self) -> None:
        super(PipelinePlugin, self).__init__()
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
        ctx: typer.Context,
        file: Path = typer.Option("wanna.yaml", "--file", "-f", help="Path to the wanna-ml yaml configuration"),
        version: str = typer.Option("dev", "--version", "-v", help="Pipeline version"),
        instance_name: str = typer.Option(
            "all",
            "--name",
            "-n",
            help="Specify only one pipeline from your wanna-ml yaml configuration to compile. "
            "Choose 'all' to compile all pipelines.",
        ),
    ) -> None:
        config = load_config_from_yaml(file)
        workdir = pathlib.Path(file).parent
        pipeline_service = PipelineService(config=config, workdir=workdir, version=version)
        pipeline_service.build(instance_name)

    @staticmethod
    def push(
        ctx: typer.Context,
        file: Path = typer.Option("wanna.yaml", "--file", "-f", help="Path to the wanna-ml yaml configuration"),
        version: str = typer.Option(..., "--version", "-v", help="Pipeline version"),
        instance_name: str = typer.Option(
            "all",
            "--name",
            "-n",
            help="Specify only one pipeline from your wanna-ml yaml configuration to compile. "
            "Choose 'all' to push all pipelines.",
        ),
    ) -> None:
        config = load_config_from_yaml(file)
        workdir = pathlib.Path(file).parent
        pipeline_service = PipelineService(config=config, workdir=workdir, version=version)
        pipelines = pipeline_service.build(instance_name)
        pipeline_service.push(pipelines, version)

    @staticmethod
    def deploy(
        ctx: typer.Context,
        file: Path = typer.Option("wanna.yaml", "--file", "-f", help="Path to the wanna-ml yaml configuration"),
        version: str = typer.Option(..., "--version", "-v", help="Pipeline version"),
        env: str = typer.Option("local", "--env", "-e", help="Pipeline env"),
        instance_name: str = typer.Option(
            "all",
            "--name",
            "-n",
            help="Specify only one pipeline from your wanna-ml yaml configuration to compile. "
            "Choose 'all' to push all pipelines.",
        ),
    ) -> None:
        config = load_config_from_yaml(file)
        workdir = pathlib.Path(file).parent
        pipeline_service = PipelineService(config=config, workdir=workdir, version=version)
        pipeline_service.deploy(instance_name, version, env)

    @staticmethod
    def run(
        ctx: typer.Context,
        file: Optional[Path] = typer.Option(None, "--file", "-f", help="Path to the wanna-ml yaml configuration"),
        version: str = typer.Option("dev", "--version", "-v", help="Pipeline version"),
        manifest: Optional[str] = typer.Option(
            None, "--manifest", "-m", help="Path to the wanna-manifest.json configuration"
        ),
        params: Path = typer.Option("params.yaml", "--params", "-p", help="Path to the params file in yaml format"),
        sync: bool = typer.Option(False, "--sync", "-s", help="Runs the pipeline in sync mode"),
        instance_name: str = typer.Option(
            "all",
            "--name",
            "-n",
            help="Specify only one pipeline from your wanna-ml yaml configuration to run."
            "Choose 'all' to run all pipelines sequentially.",
        ),
    ) -> None:
        if file:
            config = load_config_from_yaml(file)
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
