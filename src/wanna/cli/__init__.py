# mypy: allow-untyped-calls
from importlib import metadata as importlib_metadata

try:
    __version__ = importlib_metadata.version(__name__)
except importlib_metadata.PackageNotFoundError:
    __version__ = "snapshot"
