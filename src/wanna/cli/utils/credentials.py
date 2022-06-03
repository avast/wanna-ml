import functools
import os
from typing import Optional

from google import auth
from google.auth import impersonated_credentials
from google.auth.credentials import Credentials
from google.auth.exceptions import DefaultCredentialsError

from wanna.cli.utils.spinners import Spinner


@functools.lru_cache(maxsize=1)
def get_credentials() -> Optional[Credentials]:
    impersonate_account = os.getenv("WANNA_IMPERSONATE_ACCOUNT")
    target_scopes = ["https://www.googleapis.com/auth/cloud-platform"]

    try:
        _credentials, _ = auth.default()

        if impersonate_account and _credentials:
            credentials = impersonated_credentials.Credentials(
                source_credentials=_credentials,
                target_principal=impersonate_account,
                target_scopes=_credentials.scopes or target_scopes,
                lifetime=500,
            )
            return credentials
        else:
            return None

    except DefaultCredentialsError:
        Spinner().info(
            "f default credentials were not found you likely need to execute " "`gcloud auth application-default login`"
        )
        exit(1)
