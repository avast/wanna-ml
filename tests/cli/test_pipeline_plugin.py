import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from mock import patch
from typer.testing import CliRunner

from tests.mocks import mocks
from wanna.cli.plugins.pipeline_plugin import PipelinePlugin
from wanna.core.utils.env import reload_setup


@patch(
    "wanna.core.services.pipeline.VertexConnector",
    mocks.MockVertexPipelinesMixInVertex,
)
@patch("wanna.core.services.docker.docker", new=MagicMock())
class TestPipelinePlugin(unittest.TestCase):
    runner = CliRunner()
    plugin = PipelinePlugin()
    parent = Path(__file__).parent.parent.parent
    wanna_path = parent / "samples" / "pipelines" / "sklearn" / "wanna.yaml"
    manifest_path = (
        parent
        / "samples"
        / "pipelines"
        / "sklearn"
        / "build"
        / "wanna-pipelines"
        / "wanna-sklearn-sample"
        / "deployment"
        / "test"
        / "manifests"
        / "wanna-manifest.json"
    )

    def setUp(self):
        self.original_env = os.environ.copy()
        os.environ["WANNA_GCP_ACCESS_ALLOWED"] = "false"
        os.environ["WANNA_GCP_ENABLE_REMOTE_VALIDATION"] = "false"
        reload_setup()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)
        reload_setup()

    @patch("wanna.core.services.pipeline.PipelineService.build")
    def test_pipeline_build_cli(self, build_patch):
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
        build_patch.assert_called_once()
        build_patch.assert_called_with("wanna-sklearn-sample", None)

        self.assertEqual(0, result.exit_code)

    @patch("wanna.core.services.pipeline.PipelineService.run")
    @patch("wanna.core.services.pipeline.PipelineService.build", return_value=[manifest_path])
    @patch("wanna.core.services.pipeline.PipelineService.push")
    def test_pipeline_run_cli(self, push_patch, build_patch, run_patch):
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
        push_patch.assert_called_once()
        build_patch.assert_called_once()
        run_patch.assert_called_once()
        push_patch.assert_called_with(build_patch.return_value, local=False)
        build_patch.assert_called_with("wanna-sklearn-sample")
        run_patch.assert_called_with([str(self.manifest_path)], extra_params=None, sync=False)
        self.assertEqual(0, result.exit_code)

    @patch("wanna.core.services.pipeline.PipelineService.build", return_value=[manifest_path])
    @patch("wanna.core.services.pipeline.PipelineService.push")
    def test_pipeline_push_cli(self, push_patch, build_patch):
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

        build_patch.assert_called_once()
        build_patch.assert_called_with("wanna-sklearn-sample", None)
        push_patch.assert_called_once()
        push_patch.assert_called_with([self.manifest_path])
        self.assertEqual(0, result.exit_code)

    @patch("wanna.core.services.pipeline.PipelineService.deploy")
    def test_pipeline_deploy_cli(self, deploy_patch):
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

        deploy_patch.assert_called_once()
        deploy_patch.assert_called_with("wanna-sklearn-sample", "local")
        self.assertEqual(0, result.exit_code)

    @patch("wanna.core.services.pipeline.PipelineService.run")
    def test_notebook_run_manifest_cli(self, run_patch):
        manifest_file = str(self.manifest_path)
        result = self.runner.invoke(
            self.plugin.app,
            [
                "run-manifest",
                "--manifest",
                manifest_file,
            ],
        )
        run_patch.assert_called_once()
        run_patch.assert_called_with([manifest_file], extra_params=None, sync=False)

        self.assertEqual(0, result.exit_code)

    @patch("wanna.core.services.pipeline.PipelineService.report")
    def test_pipeline_report_cli(self, report_patch):
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
        report_patch.assert_called_once()
        report_patch.assert_called_with(
            billing_id=None,
            gcp_project="your-gcp-project-id",
            instance_name="wanna-sklearn-sample",
            organization_id=None,
            wanna_project="pipeline-sklearn-example-1",
            wanna_resource="pipeline",
        )

        self.assertEqual(0, result.exit_code)
