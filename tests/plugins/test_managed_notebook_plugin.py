import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from mock import patch
from typer.testing import CliRunner

from tests.mocks import mocks
from wanna.cli.plugins.managed_notebook_plugin import ManagedNotebookPlugin
from wanna.core.services.managed_notebook import ManagedNotebookService


@patch(
    "wanna.core.services.managed_notebook.ManagedNotebookServiceClient",
    mocks.MockManagedNotebookServiceClient,
)
class TestManagedNotebookPlugin(unittest.TestCase):
    runner = CliRunner()
    plugin = ManagedNotebookPlugin()
    parent = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
    wanna_path = parent / "samples" / "notebook" / "managed-notebook" / "wanna.yaml"

    def test_managed_notebook_create_cli(self):
        ManagedNotebookService.create = MagicMock()

        result = self.runner.invoke(
            self.plugin.app,
            [
                "create",
                "--file",
                self.wanna_path,
                "--name",
                "minimum-setup",
                "--profile",
                "default",
            ],
        )
        ManagedNotebookService.create.assert_called_once()
        ManagedNotebookService.create.assert_called_with("minimum-setup")

        self.assertEqual(0, result.exit_code)

    def test_managed_notebook_delete_cli(self):
        ManagedNotebookService.delete = MagicMock()

        result = self.runner.invoke(
            self.plugin.app,
            [
                "delete",
                "--file",
                str(self.wanna_path),
                "--name",
                "minimum-setup",
                "--profile",
                "default",
            ],
        )
        ManagedNotebookService.delete.assert_called_once()
        ManagedNotebookService.delete.assert_called_with("minimum-setup")
        self.assertEqual(0, result.exit_code)

    def test_managed_notebook_build_cli(self):
        ManagedNotebookService.build = MagicMock()
        result = self.runner.invoke(
            self.plugin.app,
            [
                "build",
                "--file",
                str(self.wanna_path),
            ],
        )
        ManagedNotebookService.build.assert_called_once()
        self.assertEqual(0, result.exit_code)

    def test_managed_notebook_report_cli(self):
        ManagedNotebookService.report = MagicMock()
        result = self.runner.invoke(
            self.plugin.app,
            [
                "report",
                "--file",
                str(self.wanna_path),
                "--name",
                "minimum-setup",
            ],
        )
        ManagedNotebookService.report.assert_called_with(
            instance_name="minimum-setup",
            wanna_project="wanna-notebook-sample",
            wanna_resource="managed_notebook",
            gcp_project="your-gcp-project-id",
            billing_id="your-billing-id",
            organization_id="your-organization-id",
        )
        self.assertEqual(0, result.exit_code)
