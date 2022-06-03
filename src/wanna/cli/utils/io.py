import contextlib

from google.cloud.storage import Client
from smart_open import open as gcs_open

from wanna.cli.utils.credentials import get_credentials


@contextlib.contextmanager
def open(*args, **kwargs):
    with gcs_open(*args, transport_params=dict(client=Client(credentials=get_credentials())), **kwargs) as c:
        yield c
