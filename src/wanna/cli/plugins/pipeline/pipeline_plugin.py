import pathlib
from pathlib import Path

import typer

from wanna.cli.plugins.base.base_plugin import BasePlugin
from wanna.cli.plugins.pipeline.service import PipelineService
from wanna.cli.utils.config_loader import load_config_from_yaml


class PipelinePlugin(BasePlugin):
    def __init__(self) -> None:
        super(PipelinePlugin, self).__init__()
        self.register_many([self.compile, self.run])

    @staticmethod
    def compile(
        ctx: typer.Context,
        file: Path = typer.Option("wanna.yaml", "--file", "-f", help="Path to the wanna-ml yaml configuration"),
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
        pipeline_service = PipelineService(config=config, workdir=workdir)
        pipeline_service.compile(instance_name)

    @staticmethod
    def run(
        ctx: typer.Context,
        file: Path = typer.Option("wanna.yaml", "--file", "-f", help="Path to the wanna-ml yaml configuration"),
        params: Path = typer.Option("params.yaml", "--params", "-p", help="Path to the params file in yaml format"),
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
        pipeline_service = PipelineService(config=config, workdir=workdir)
        pipelines = pipeline_service.compile(instance_name)
        pipeline_service.run(pipelines, extra_params_path=params)
