import re
from datetime import datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, List, Optional, Union

import requests
import typer
from packaging import version

from wanna.core.loggers.wanna_logger import get_logger

from .. import __version__

logger = get_logger(__name__)

ARTIFACTORY_URL = "https://artifactory.ida.avast.com/artifactory/api/pypi/pypi-local/simple/wanna-ml/"
VERSION_CHECK_FILE = "last_version_check"
UPDATE_MESSAGE = (
    "If you used `pipx` to install Schnitzel CLI, use the following command:\n\n"
    "pipx upgrade wanna\n\n"
    f"Otherwise, use `pip install --upgrade {__package__}`"
    "(exact command will depend on your environment).\n\n"
)

Version = Union[version.Version, version.LegacyVersion]


class PyPiSimpleParser(HTMLParser):
    """A parser that only handles pages of the "simple" PyPI index."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:

        super().__init__(*args, **kwargs)

        self.packages: List[str] = []

    def handle_data(self, data: str) -> None:
        if ".tar.gz" in data:
            self.packages.append(data)


def _get_version(artifact_name: str) -> Optional[Version]:

    pattern = r"""^{}-  #package name
                  ((\d+\.)?(\d+\.)?\d+)  # version like 0.0.0, 0.0 or 0
                  .tar.gz$""".format(
        __package__
    )

    compiled = re.compile(pattern, re.VERBOSE)
    match = re.match(compiled, artifact_name)

    if match:
        return version.parse(match.group(1))
    else:
        return None


def get_latest_version() -> Optional[Version]:
    """Retrieve and parse the Artifactory PyPI page for this package. Return
    the latest available version."""

    parser = PyPiSimpleParser()

    try:
        resp = requests.get(ARTIFACTORY_URL)
        resp.raise_for_status()
    except (ConnectionError, requests.exceptions.RequestException):
        logger.exception("Failed to retrieve versions")
        return None

    parser.feed(resp.text)

    versions = list(filter(bool, (_get_version(package) for package in parser.packages)))

    if not versions:
        return None

    return max(version for version in versions if version is not None)


def do_check_version(app_path: Path, interval: timedelta = timedelta(hours=24)) -> bool:
    """Check if it is time to perform a check for new versions.
    Time of last check is read from a file saved in the application directory.
    `interval` can be passed to control how old the last check can be to be
    accepteed (24 hours by default).
    If it is time to perform a check, current time is written to the file."""

    version_check_file = app_path.joinpath(VERSION_CHECK_FILE)
    now = datetime.now()
    if version_check_file.exists():
        try:
            timestamp = float(version_check_file.read_text().strip())
        except ValueError:
            version_check_file.write_text(str(now.timestamp()))
            return True

        time = datetime.fromtimestamp(timestamp)

        if now - time > interval:
            version_check_file.write_text(str(now.timestamp()))
            return True
        else:
            return False
    else:
        version_check_file.write_text(str(now.timestamp()))
        return True


def perform_check(terminate: bool = True) -> None:
    """Perform the check and interact with the user.
    This function can be used as an option callback, or directly. If `eager` is
    True, the function will terminate the CLI execution."""

    latest_version = get_latest_version()
    if latest_version and version.Version(__version__) < latest_version:
        logger.user_error(
            f"Installed version is {__version__}, the latest version is {latest_version}",
        )
        logger.user_info(
            UPDATE_MESSAGE,
            fg="yellow",
        )
        if terminate or typer.confirm(
            "Would you like to install update now? (wanna will be terminated)",
            default=False,
        ):
            typer.Exit()
    else:
        logger.user_success(f"Your wanna cli is up to date with {latest_version}")
        if terminate:
            typer.Exit()
