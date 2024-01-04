import functools
import os
from typing import Optional

import gcloud_config_helper
from google import auth
from google.auth import impersonated_credentials
from google.auth.credentials import Credentials
from google.auth.exceptions import DefaultCredentialsError

from wanna.core.loggers.wanna_logger import get_logger
from wanna.core.utils.env import gcp_access_allowed

logger = get_logger(__name__)


@functools.lru_cache(maxsize=1)
def get_credentials() -> Optional[Credentials]:
    if gcp_access_allowed:
        impersonate_account = os.getenv("WANNA_IMPERSONATE_ACCOUNT")
        target_scopes = ["https://www.googleapis.com/auth/cloud-platform"]

        try:
            if impersonate_account:
                _credentials, _ = auth.default()
                credentials = impersonated_credentials.Credentials(
                    source_credentials=_credentials,
                    target_principal=impersonate_account,
                    target_scopes=_credentials.scopes
                    if _credentials and _credentials.scopes
                    else target_scopes,
                    lifetime=500,
                )
                return credentials
            else:
                return None

        except DefaultCredentialsError as e:
            logger.user_info(
                f"{e}\ndefault credentials were not found you likely need to execute"
                "`gcloud auth application-default login`"
            )
            exit(1)

    return None


def get_gcloud_user() -> str:
    if gcp_access_allowed:
        credentials, project = gcloud_config_helper.default()
        return credentials.properties.get("core", {}).get("account", "unidentified")[
            :60
        ]

    return "no-gcp-access-not-allowed"
