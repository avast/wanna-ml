import os
from pathlib import Path
from string import Template
from typing import TYPE_CHECKING

from lazyimport import Import

if TYPE_CHECKING:  # pragma: no cover
    import kfp.components as comp
else:
    comp = Import("kfp.components")


def load_wanna_component(path: Path | str):
    with open(str(path), encoding="utf-8") as f:
        t = Template(f.read())
        component = t.safe_substitute(os.environ)
        return comp.load_component_from_text(component)
