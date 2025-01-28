import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from mock import patch
from typer.testing import CliRunner

from tests.mocks import mocks
from wanna.cli.plugins.pipeline_plugin import PipelinePlugin
from wanna.core.services.pipeline import PipelineService


@patch(
    "wanna.core.services.pipeline.VertexConnector",
    mocks.MockVertexPipelinesMixInVertex,
)
@patch(
    "wanna.core.services.pipeline.DockerService",
    mocks.MockDockerService,
)
class TestPipelinePlugin(unittest.TestCase):
    runner = CliRunner()
    plugin = PipelinePlugin()
    parent = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
    wanna_path = parent / "samples" / "pipelines" / "sklearn" / "wanna.yaml"

    def setUp(self):
        self.original_env = os.environ.copy()
        os.environ["WANNA_GCP_ACCESS_ALLOWED"] = "false"
        os.environ["WANNA_GCP_ENABLE_REMOTE_VALIDATION"] = "false"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_pipeline_build_cli(self):
        PipelineService.build = MagicMock()

        result = self.runner.invoke(
            self.plugin.app,
            [
                "build",
                "--file",
                self.wanna_path,
                "--name",
                "wanna-sklearn-sample",
                "--mode",
                "quick",
                "--profile",
                "default",
            ],
        )
        PipelineService.build.assert_called_once()
        PipelineService.build.assert_called_with("wanna-sklearn-sample", None)

        self.assertEqual(0, result.exit_code)

    def test_pipeline_run_cli(self):
        PipelineService.run = MagicMock()

        result = self.runner.invoke(
            self.plugin.app,
            [
                "run",
                "--file",
                str(self.wanna_path),
                "--name",
                "wanna-sklearn-sample",
                "--profile",
                "default",
            ],
        )
        PipelineService.run.assert_called_once()
        PipelineService.run.assert_called_with([], extra_params=None, sync=False)
        self.assertEqual(0, result.exit_code)

    def test_pipeline_push_cli(self):
        PipelineService.push = MagicMock()
        result = self.runner.invoke(
            self.plugin.app,
            [
                "push",
                "--file",
                str(self.wanna_path),
                "--name",
                "wanna-sklearn-sample",
                "--profile",
                "default",
            ],
        )

        PipelineService.push.assert_called_once()

        self.assertEqual(0, result.exit_code)

    def test_pipeline_deploy_cli(self):
        PipelineService.deploy = MagicMock()
        result = self.runner.invoke(
            self.plugin.app,
            [
                "deploy",
                "--file",
                str(self.wanna_path),
                "--name",
                "wanna-sklearn-sample",
                "--profile",
                "default",
            ],
        )

        PipelineService.deploy.assert_called_once()

        self.assertEqual(0, result.exit_code)

    def test_notebook_build(self):
        PipelineService.build = MagicMock()
        result = self.runner.invoke(
            self.plugin.app,
            [
                "build",
                "--file",
                str(self.wanna_path),
            ],
        )
        PipelineService.build.assert_called_once()
        self.assertEqual(0, result.exit_code)

    def test_notebook_run_manifest_cli(self):
        # to build the manifest
        self.runner.invoke(
            self.plugin.app,
            [
                "build",
                "--file",
                self.wanna_path,
                "--name",
                "wanna-sklearn-sample",
                "--mode",
                "quick",
                "--profile",
                "default",
            ],
        )

        PipelineService.run = MagicMock()
        manifest_file = (
            self.wanna_path.parent
            / "build"
            / "wanna-pipelines"
            / "wanna-sklearn-sample"
            / "deployment"
            / "test"
            / "manifests"
            / "wanna-manifest.json"
        )
        result = self.runner.invoke(
            self.plugin.app,
            [
                "run-manifest",
                "--manifest",
                str(manifest_file),
            ],
        )
        PipelineService.run.assert_called_once()
        PipelineService.run.assert_called_with([str(manifest_file)], extra_params=None, sync=False)

        self.assertEqual(0, result.exit_code)

    def test_pipeline_report_cli(self):
        PipelineService.report = MagicMock()

        result = self.runner.invoke(
            self.plugin.app,
            [
                "report",
                "--file",
                str(self.wanna_path),
                "--name",
                "wanna-sklearn-sample",
                "--profile",
                "default",
            ],
        )
        PipelineService.report.assert_called_once()
        PipelineService.report.assert_called_with(
            billing_id=None,
            gcp_project="your-gcp-project-id",
            instance_name="wanna-sklearn-sample",
            organization_id=None,
            wanna_project="pipeline-sklearn-example-1",
            wanna_resource="pipeline",
        )

        self.assertEqual(0, result.exit_code)
