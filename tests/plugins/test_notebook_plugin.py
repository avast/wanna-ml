import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from mock import patch
from typer.testing import CliRunner

from tests.mocks import mocks
from wanna.cli.plugins.notebook_plugin import NotebookPlugin
from wanna.core.deployment.models import PushMode
from wanna.core.services.notebook import NotebookService


@patch(
    "wanna.core.services.notebook.NotebookServiceClient",
    mocks.MockNotebookServiceClient,
)
class TestNotebookPlugin(unittest.TestCase):
    runner = CliRunner()
    plugin = NotebookPlugin()
    parent = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
    wanna_path = parent / "samples" / "notebook" / "vm_image" / "wanna.yaml"

    def test_notebook_create_cli(self):
        NotebookService.create = MagicMock()

        result = self.runner.invoke(
            self.plugin.app,
            [
                "create",
                "--file",
                self.wanna_path,
                "--name",
                "wanna-notebook-vm",
                "--profile",
                "default",
            ],
        )
        NotebookService.create.assert_called_once()
        NotebookService.create.assert_called_with("wanna-notebook-vm", push_mode=PushMode.all)

        self.assertEqual(0, result.exit_code)

    def test_notebook_delete_cli(self):
        NotebookService.delete = MagicMock()

        result = self.runner.invoke(
            self.plugin.app,
            [
                "delete",
                "--file",
                str(self.wanna_path),
                "--name",
                "wanna-notebook-vm",
                "--profile",
                "default",
            ],
        )
        NotebookService.delete.assert_called_once()
        NotebookService.delete.assert_called_with("wanna-notebook-vm")
        self.assertEqual(0, result.exit_code)

    def test_notebook_ssh_cli(self):
        NotebookService._ssh = MagicMock()
        result = self.runner.invoke(
            self.plugin.app,
            [
                "ssh",
                "--file",
                str(self.wanna_path),
            ],
        )

        NotebookService._ssh.assert_called_once()

        self.assertEqual(0, result.exit_code)

    def test_notebook_ssh_cli_failure(self):

        result = self.runner.invoke(
            self.plugin.app,
            [
                "ssh",
                "--file",
                str(self.wanna_path),
                "--name",
                "non-existent",
            ],
        )

        self.assertEqual(1, result.exit_code)

    def test_notebook_build(self):
        NotebookService.build = MagicMock()
        result = self.runner.invoke(
            self.plugin.app,
            [
                "build",
                "--file",
                str(self.wanna_path),
            ],
        )
        NotebookService.build.assert_called_once()
        self.assertEqual(0, result.exit_code)

    def test_notebook_report(self):
        NotebookService.report = MagicMock()
        result = self.runner.invoke(
            self.plugin.app,
            [
                "report",
                "--file",
                str(self.wanna_path),
                "--name",
                "wanna-notebook-vm",
            ],
        )
        NotebookService.report.assert_called_with(
            instance_name="wanna-notebook-vm",
            wanna_project="wanna-notebook-sample",
            wanna_resource="notebook",
            gcp_project="your-gcp-project-id",
            billing_id="your-billing-id",
            organization_id="your-organization-id",
        )
        self.assertEqual(0, result.exit_code)

    def test_notebook_sync_cli(self):
        NotebookService.sync = MagicMock()

        result = self.runner.invoke(
            self.plugin.app,
            [
                "sync",
                "--file",
                self.wanna_path,
                "--profile",
                "default",
                "--force",
            ],
        )
        NotebookService.sync.assert_called_once()
        NotebookService.sync.assert_called_with(force=True, push_mode=PushMode.all)

        self.assertEqual(0, result.exit_code)

    def test_notebook_push_cli(self):
        NotebookService.push = MagicMock()

        result = self.runner.invoke(
            self.plugin.app,
            [
                "push",
                "--file",
                self.wanna_path,
            ],
        )
        NotebookService.push.assert_called_once()
        NotebookService.push.assert_called_with(instance_name="all")

        self.assertEqual(0, result.exit_code)
