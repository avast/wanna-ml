import contextlib
import json
from pathlib import Path
from typing import Any, Dict, Union

from google.cloud.storage import Client
from smart_open import open as gcs_open

from wanna.core.deployment.credentials import GCPCredentialsMixIn


class IOMixin(GCPCredentialsMixIn):
    @contextlib.contextmanager
    def _open(self, uri, mode="r", **kwargs):
        transport_params = (
            {"client": Client(credentials=self.credentials)}
            if str(uri).startswith("gs")
            else {}
        )
        with gcs_open(uri, mode, transport_params=transport_params, **kwargs) as c:
            yield c

    def upload_file(self, source: str, destination: str) -> None:
        with self._open(source, "rb") as f:
            with self._open(destination, "wb") as fout:
                fout.write(f.read())

    def write(self, destination: Union[Path, str], body: str) -> None:
        with self._open(destination, "w") as fout:
            fout.write(body)

    def read(self, source: Union[Path, str]) -> Dict[Any, Any]:
        with self._open(source, "r") as fin:
            return json.loads(fin.read())
