from __future__ import annotations

import functools
import logging
import os
from typing import TYPE_CHECKING, Union

import gcloud_config_helper
from lazyimport import Import

if TYPE_CHECKING:  # pragma: no cover
    import google.auth.credentials as google_auth_credentials
    import google.auth.exceptions as google_auth_exceptions
    import google.auth.impersonated_credentials as google_auth_impersonated_credentials
    from google import auth as google_auth
else:
    google_auth = Import("google.auth")
    google_auth_impersonated_credentials = Import("google.auth.impersonated_credentials")
    google_auth_credentials = Import("google.auth.credentials")
    google_auth_exceptions = Import("google.auth.exceptions")

from wanna.core.loggers.wanna_logger import get_logger
from wanna.core.utils.env import gcp_access_allowed

logger = get_logger(__name__)


@functools.lru_cache(maxsize=1)
def get_credentials() -> Union[google_auth_credentials.Credentials, None]:
    if gcp_access_allowed:
        impersonate_account = os.getenv("WANNA_IMPERSONATE_ACCOUNT")
        target_scopes = ["https://www.googleapis.com/auth/cloud-platform"]

        try:
            if impersonate_account:
                _credentials, _ = google_auth.default()
                credentials = google_auth_impersonated_credentials.Credentials(
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

        except google_auth_exceptions.DefaultCredentialsError as e:
            logger.user_info(
                f"{e}\ndefault credentials were not found you likely need to execute"
                "`gcloud auth application-default login`"
            )
            exit(1)

    return None


def get_gcloud_user() -> str:
    if gcp_access_allowed:
        try:
            credentials, project = gcloud_config_helper.default()
        except Exception as e:
            # to get the error, because pydantic suppresses stack traces
            logging.exception("failed to interact with gcloud")
            raise e
        return credentials.properties.get("core", {}).get("account", "unidentified")[:60]

    return "no-gcp-access-not-allowed"
