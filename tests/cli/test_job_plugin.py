import os
import unittest
from pathlib import Path

from mock.mock import patch
from typer.testing import CliRunner

from wanna.cli.plugins.job_plugin import JobPlugin


class TestJobPlugin(unittest.TestCase):
    runner = CliRunner()
    plugin = JobPlugin()
    parent = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
    test_runner_dir = parent / ".build" / "test_job_service"
    sample_job_dir = parent / "samples" / "custom_job"
    job_build_dir = sample_job_dir / "build"

    def test_job_build_cli(self):
        result = self.runner.invoke(
            self.plugin.app,
            [
                "build",
                "--file",
                str(self.sample_job_dir / "wanna.yaml"),
                "--name",
                "custom-training-job-with-containers",
                "--profile",
                "default",
            ],
        )
        self.assertEqual(0, result.exit_code)

    def test_job_push_cli(self):
        result = self.runner.invoke(
            self.plugin.app,
            [
                "push",
                "--file",
                str(self.sample_job_dir / "wanna.yaml"),
                "--name",
                "custom-training-job-with-containers",
                "--profile",
                "default",
                "--version",
                "test",
                "--mode",
                "containers",
            ],
        )
        self.assertEqual(0, result.exit_code)

        result = self.runner.invoke(
            self.plugin.app,
            [
                "push",
                "--file",
                str(self.sample_job_dir / "wanna.yaml"),
                "--name",
                "custom-training-job-with-containers",
                "--profile",
                "default",
                "--version",
                "test",
                "--mode",
                "manifests",
            ],
        )
        self.assertEqual(0, result.exit_code)

        result = self.runner.invoke(
            self.plugin.app,
            [
                "push",
                "--file",
                str(self.sample_job_dir / "wanna.yaml"),
                "--name",
                "custom-training-job-with-containers",
                "--profile",
                "default",
                "--version",
                "test",
                "--mode",
                "does-not-exist-in-enum",
            ],
        )
        self.assertEqual(2, result.exit_code)

    @patch("wanna.core.deployment.vertex_connector.VertexConnector.run_training_job")
    def test_job_run_cli(self, run_training_job_mock):
        result = self.runner.invoke(
            self.plugin.app,
            [
                "run",
                "--file",
                str(self.sample_job_dir / "wanna.yaml"),
                "--name",
                "custom-training-job-with-containers",
                "--profile",
                "default",
                "--version",
                "test",
                "--sync",
                "--hp-params",
                str(self.sample_job_dir / "hp-params.yaml"),
                "python",
                "-m",
                "magic.module",
                "--dataset",
                "gs://..",
            ],
        )
        self.assertEqual(0, result.exit_code)
        run_training_job_mock.assert_called()

        # should work without sync and hp-params
        result = self.runner.invoke(
            self.plugin.app,
            [
                "run",
                "--file",
                str(self.sample_job_dir / "wanna.yaml"),
                "--name",
                "custom-training-job-with-containers",
                "--profile",
                "default",
                "--version",
                "test",
                "python",
                "-m",
                "magic.module",
                "--dataset",
                "gs://..",
            ],
        )
        self.assertEqual(0, result.exit_code)

    @patch("wanna.core.services.jobs.JobService.run")
    def test_job_run_manifest_cli(self, run_patch):
        result = self.runner.invoke(
            self.plugin.app,
            [
                "run-manifest",
                "--manifest",
                str(self.sample_job_dir / "wanna.yaml"),
                "--sync",
                "--hp-params",
                str(self.sample_job_dir / "hp-params.yaml"),
                "python",
                "-m",
                "magic.module",
                "--dataset",
                "gs://..",
            ],
        )

        run_patch.assert_called_with(
            manifests=[str(self.sample_job_dir / "wanna.yaml")],
            sync=True,
            hp_params=self.sample_job_dir / "hp-params.yaml",
            command_override=["python", "-m", "magic.module"],
            args_override=["--dataset", "gs://.."],
        )

        self.assertEqual(0, result.exit_code)

    @patch("wanna.core.services.jobs.JobService.stop")
    def test_job_stop(self, stop_patch):
        result = self.runner.invoke(
            self.plugin.app,
            [
                "stop",
                "--file",
                str(self.sample_job_dir / "wanna.yaml"),
                "--name",
                "custom-training-job-with-containers",
                "--profile",
                "default",
            ],
        )

        stop_patch.assert_called_with("custom-training-job-with-containers")

        self.assertEqual(0, result.exit_code)

    @patch("wanna.core.services.jobs.JobService.report")
    def test_job_report(self, report_patch):
        result = self.runner.invoke(
            self.plugin.app,
            [
                "report",
                "--file",
                str(self.sample_job_dir / "wanna.yaml"),
                "--name",
                "custom-training-job-with-containers",
                "--profile",
                "default",
            ],
        )

        report_patch.assert_called_with(
            instance_name="custom-training-job-with-containers",
            wanna_project="wanna-custom-job-sample",
            wanna_resource="job",
            gcp_project="your-gcp-project-id",
            billing_id=None,
            organization_id=None,
        )

        self.assertEqual(0, result.exit_code)
