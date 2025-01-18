import os
import unittest
from pathlib import Path

from mock.mock import MagicMock
from typer.testing import CliRunner

from wanna.cli.plugins.job_plugin import JobPlugin
from wanna.core.deployment.models import JobResource
from wanna.core.deployment.vertex_connector import VertexConnector
from wanna.core.models.training_custom_job import TrainingCustomJobModel
from wanna.core.services import jobs


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

    def test_job_run_cli(self):
        VertexConnector[JobResource[TrainingCustomJobModel]].run_training_job = MagicMock()

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
        VertexConnector[JobResource[TrainingCustomJobModel]].run_training_job.assert_called()

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

    def test_job_run_manifest_cli(self):
        jobs.JobService.run = MagicMock()

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

        jobs.JobService.run.assert_called_with(
            manifests=[str(self.sample_job_dir / "wanna.yaml")],
            sync=True,
            hp_params=self.sample_job_dir / "hp-params.yaml",
            command_override=["python", "-m", "magic.module"],
            args_override=["--dataset", "gs://.."],
        )

        self.assertEqual(0, result.exit_code)
