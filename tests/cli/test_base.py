import unittest
from pathlib import Path
from unittest.mock import MagicMock

from typer.testing import CliRunner

from wanna.cli import __main__


class TestJobPlugin(unittest.TestCase):
    def test_version(self):
        result = CliRunner().invoke(
            __main__.app,
            [
                "version",
            ],
        )
        assert result.exit_code == 0

    def test_init(self):
        __main__.cookiecutter = MagicMock()
        result = CliRunner().invoke(
            __main__.app,
            [
                "init",
                "--output-dir",
                str(Path(__file__).parent.parent.resolve()),
                "--template",
                "https://github.com/avast/wanna-ml-cookiecutter",
                "--overwrite-if-exists",
                "--no-input",
            ],
        )
        assert result.exit_code == 0
