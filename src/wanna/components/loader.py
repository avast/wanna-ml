import os
from pathlib import Path
from string import Template

import kfp.components as comp


def load_wanna_component(path: Path | str):
    with open(str(path), encoding="utf-8") as f:
        t = Template(f.read())
        component = t.safe_substitute(os.environ)
        return comp.load_component_from_text(component)
