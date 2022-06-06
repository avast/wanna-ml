import contextlib

from google.cloud.storage import Client
from smart_open import open as gcs_open

from wanna.cli.utils.credentials import get_credentials


@contextlib.contextmanager
def open(uri, mode="r", **kwargs):
    transport_params = {"client": Client(credentials=get_credentials())} if str(uri).startswith("gs") else {}
    with gcs_open(uri, mode, transport_params=transport_params, **kwargs) as c:
        yield c
