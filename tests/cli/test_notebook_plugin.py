import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from mock import patch
from typer.testing import CliRunner

from tests.mocks import mocks
from wanna.cli.plugins.notebook_plugin import NotebookPlugin
from wanna.core.deployment.models import PushMode
from wanna.core.services.workbench_instance import WorkbenchInstanceService


@patch(
    "wanna.core.services.workbench_instance.NotebookServiceClient",
    mocks.MockWorkbenchInstanceServiceClient,
)
class TestNotebookPlugin(unittest.TestCase):
    runner = CliRunner()
    plugin = NotebookPlugin()
    parent = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
    wanna_path = parent / "samples" / "notebook" / "vm_image" / "wanna.yaml"

    @patch("wanna.core.services.workbench_instance.WorkbenchInstanceService.create")
    def test_notebook_create_cli(self, create_patch):
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
        create_patch.assert_called_once()
        create_patch.assert_called_with("wanna-notebook-vm", push_mode=PushMode.all)

        self.assertEqual(0, result.exit_code)

    @patch("wanna.core.services.workbench_instance.WorkbenchInstanceService.delete")
    def test_notebook_delete_cli(self, delete_patch):
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
        delete_patch.assert_called_once()
        delete_patch.assert_called_with("wanna-notebook-vm")
        self.assertEqual(0, result.exit_code)

    @patch("wanna.core.services.workbench_instance.WorkbenchInstanceService._ssh")
    def test_notebook_ssh_cli(self, ssh_patch):
        result = self.runner.invoke(
            self.plugin.app,
            [
                "ssh",
                "--file",
                str(self.wanna_path),
            ],
        )

        ssh_patch.assert_called_once()

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

    @patch("wanna.core.services.workbench_instance.WorkbenchInstanceService.build")
    def test_notebook_build(self, build_patch):
        result = self.runner.invoke(
            self.plugin.app,
            [
                "build",
                "--file",
                str(self.wanna_path),
            ],
        )
        build_patch.assert_called_once()
        self.assertEqual(0, result.exit_code)

    @patch("wanna.core.services.workbench_instance.WorkbenchInstanceService.report")
    def test_notebook_report(self, report_patch):
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
        report_patch.assert_called_with(
            instance_name="wanna-notebook-vm",
            wanna_project="wanna-notebook-sample",
            wanna_resource="notebook",
            gcp_project="your-gcp-project-id",
            billing_id="your-billing-id",
            organization_id="your-organization-id",
        )
        self.assertEqual(0, result.exit_code)

    @patch("wanna.core.services.workbench_instance.WorkbenchInstanceService.sync")
    def test_notebook_sync_cli(self, sync_patch):
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
        sync_patch.assert_called_once()
        sync_patch.assert_called_with(force=True, push_mode=PushMode.all)

        self.assertEqual(0, result.exit_code)

    @patch("wanna.core.services.workbench_instance.WorkbenchInstanceService.push")
    def test_notebook_push_cli(self, push_patch):
        result = self.runner.invoke(
            self.plugin.app,
            [
                "push",
                "--file",
                self.wanna_path,
            ],
        )
        push_patch.assert_called_once()
        push_patch.assert_called_with(instance_name="all")

        self.assertEqual(0, result.exit_code)
