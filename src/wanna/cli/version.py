import json

import pkg_resources
import requests

from wanna.core.loggers.wanna_logger import get_logger

logger = get_logger(__name__)

PYPI_URL = "https://pypi.org/pypi/wanna-ml/json"
UPDATE_MESSAGE = (
    "If you used `pipx` to install WANNA CLI, use the following command:\n\n"
    "pipx upgrade wanna-ml\n\n"
    "Otherwise, use `pip install --upgrade wanna-ml`"
    "(exact command will depend on your environment).\n\n"
)


def get_latest_version() -> str:
    try:
        resp = requests.get(PYPI_URL)
        resp.raise_for_status()
    except (ConnectionError, requests.exceptions.RequestException):
        logger.exception("Failed to retrieve versions")
        return ""
    data = json.loads(resp.text)
    return data["info"]["version"]


def perform_check() -> None:
    """Perform the version check and instructs the user about the next steps"""

    latest_version = get_latest_version()
    version = pkg_resources.get_distribution("wanna-ml").version
    if latest_version and version < latest_version:
        logger.user_error(
            f"Installed version is {version}, the latest version is {latest_version}",
        )
        logger.user_info(
            UPDATE_MESSAGE,
        )
    else:
        logger.user_success(f"Your wanna cli is up to date with {latest_version}")
