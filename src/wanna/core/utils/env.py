import os
from typing import Optional

from wanna.core.loggers.wanna_logger import get_logger

logger = get_logger(__name__)


def get_env_bool(value: Optional[str], fallback: bool) -> bool:
    """
    Checks if a str value can be considered True or False,
        mostly used to extract bool values from env vars

    Returns:
        bool from extracted value
    """
    if value in ["False", "false", "0"]:
        return False
    elif value in ["True", "true", "1"]:
        return True
    else:
        return fallback


def _gcp_access_allowed(env_var="WANNA_GCP_ACCESS_ALLOWED"):
    """
    Based on WANNA_GCP_ACCESS_ALLOWED env var checks if wanna can access GCP
    required for on-prem build environments without access to GCP

    Returns:
        bool if wanna can access GCP apis
    """
    allowed = get_env_bool(os.environ.get(env_var), True)
    logger.user_info(f"WANNA GCP access {'NOT ' if not allowed else ''}allowed")
    return allowed


gcp_access_allowed = _gcp_access_allowed()
