import contextlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from lazyimport import Import

if TYPE_CHECKING:  # pragma: no cover
    import google.cloud.storage as gcloud_storage
    import smart_open
else:
    gcloud_storage = Import("google.cloud.storage")
    smart_open = Import("smart_open")

from wanna.core.deployment.credentials import GCPCredentialsMixIn


class IOMixin(GCPCredentialsMixIn):
    @contextlib.contextmanager
    def _open(self, uri, mode="r", **kwargs):
        transport_params = (
            {"client": gcloud_storage.Client(credentials=self.credentials)}
            if str(uri).startswith("gs")
            else {}
        )
        with smart_open.open(uri, mode, transport_params=transport_params, **kwargs) as c:
            yield c

    def upload_file(self, source: str, destination: str) -> None:
        with self._open(source, "rb") as f:
            with self._open(destination, "wb") as fout:
                fout.write(f.read())

    def write(self, destination: Path | str, body: str) -> None:
        with self._open(destination, "w") as fout:
            fout.write(body)

    def read(self, source: Path | str) -> dict[Any, Any]:
        with self._open(source, "r") as fin:
            return json.loads(fin.read())
