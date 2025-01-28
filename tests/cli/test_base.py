from pathlib import Path

from typer.testing import CliRunner

from wanna.cli.__main__ import app


def test_version():
    result = CliRunner().invoke(
        app,
        [
            "version",
        ],
    )
    assert result.exit_code == 0


def test_init():
    result = CliRunner().invoke(
        app,
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
