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
from wanna.core.utils.config_loader import load_config_from_yaml


class PipelinePlugin(BasePlugin):
    """
    Plugin for building and deploying Vertex-AI ML Pipelines.
    """

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
        version: str = version_option(instance_type="pipeline"),
        params: Path = typer.Option(
            None,
            "--params",
            envvar="WANNA_ENV_PIPELINE_PARAMS",
            help="Path to the params file in yaml format",
        ),
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("pipeline", "compile"),
        mode: PushMode = push_mode_option,
    ) -> None:
        """
        Create a manifest based on the wanna-ml config that can be later pushed, deployed or run.
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent

        # doing this import here speeds up the CLI app considerably
        from wanna.core.services.pipeline import PipelineService

        pipeline_service = PipelineService(
            config=config, workdir=workdir, version=version, push_mode=mode
        )
        pipeline_service.build(instance_name, params)

    @staticmethod
    def push(
        version: str = version_option(instance_type="pipeline"),
        params: Path = typer.Option(
            None,
            "--params",
            envvar="WANNA_ENV_PIPELINE_PARAMS",
            help="Path to the params file in yaml format",
        ),
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("pipeline", "push"),
        mode: PushMode = push_mode_option,
    ) -> None:
        """
        Build and push manifest to Cloud Storage.
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent

        # doing this import here speeds up the CLI app considerably
        from wanna.core.services.pipeline import PipelineService

        pipeline_service = PipelineService(
            config=config, workdir=workdir, version=version, push_mode=mode
        )
        manifests = pipeline_service.build(instance_name, params)
        pipeline_service.push(manifests)

    @staticmethod
    def deploy(
        version: str = version_option(instance_type="pipeline"),
        env: str = typer.Option("local", "--env", "-e", help="Pipeline env"),
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("pipeline", "deploy"),
    ) -> None:
        """
        Deploy the pipeline. Deploying means you can set a schedule and the pipeline will not be run only once,
        but on regular basis.
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent

        # doing this import here speeds up the CLI app considerably
        from wanna.core.services.pipeline import PipelineService

        pipeline_service = PipelineService(
            config=config, workdir=workdir, version=version
        )
        pipeline_service.deploy(instance_name, env)

    @staticmethod
    def run(
        version: str = version_option(instance_type="pipeline notebook"),
        params: Path = typer.Option(
            None,
            "--params",
            envvar="WANNA_ENV_PIPELINE_PARAMS",
            help="Path to the params file in yaml format",
        ),
        sync: bool = typer.Option(
            False, "--sync", "-s", help="Runs the pipeline in sync mode"
        ),
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("pipeline", "run"),
        mode: PushMode = push_mode_option,
        skip_execution_cache: bool = typer.Option(
            False,
            "--skip-execution-cache",
            help="Kubeflow pipeline cache configuration",
        ),
    ) -> None:
        """
        Run the pipeline as specified in wanna-ml config. This command puts together build, push and run-manifest steps.
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent

        # doing this import here speeds up the CLI app considerably
        from wanna.core.services.pipeline import PipelineService

        pipeline_service = PipelineService(
            config=config,
            workdir=workdir,
            version=version,
            push_mode=mode,
            kubeflow_pipeline_caching=skip_execution_cache,
        )
        manifests = pipeline_service.build(instance_name)
        pipeline_service.push(manifests, local=False)
        PipelineService.run([str(p) for p in manifests], extra_params=params, sync=sync)

    @staticmethod
    def run_manifest(
        manifest: str = typer.Option(
            None, "--manifest", "-v", help="Job deployment manifest"
        ),
        params: Path = typer.Option(
            None,
            "--params",
            envvar="WANNA_ENV_PIPELINE_PARAMS",
            help="Path to the params file in yaml format",
        ),
        sync: bool = typer.Option(
            False, "--sync", "-s", help="Runs the pipeline in sync mode"
        ),
    ) -> None:
        """
        Run the pipeline as specified in the wanna-ml manifest.
        """

        # doing this import here speeds up the CLI app considerably
        from wanna.core.services.pipeline import PipelineService

        PipelineService.run([manifest], extra_params=params, sync=sync)

    @staticmethod
    def report(
        file: Path = wanna_file_option,
        profile_name: str = profile_name_option,
        instance_name: str = instance_name_option("pipeline", "report"),
    ) -> None:
        """
        Displays a link to the cost report per wanna_project and optionally per instance name.
        """
        config = load_config_from_yaml(file, gcp_profile_name=profile_name)
        workdir = pathlib.Path(file).parent

        # doing this import here speeds up the CLI app considerably
        from wanna.core.services.pipeline import PipelineService

        pipeline_service = PipelineService(config=config, workdir=workdir)
        pipeline_service.report(
            instance_name=instance_name,
            wanna_project=config.wanna_project.name,
            wanna_resource="pipeline",
            gcp_project=config.gcp_profile.project_id,
            billing_id=config.wanna_project.billing_id,
            organization_id=config.wanna_project.organization_id,
        )
