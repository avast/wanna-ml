import os
from pathlib import Path
from string import Template
from typing import Union

import kfp.components as comp


def load_wanna_component(path: Union[Path, str]):
    with open(str(path), "r") as f:
        t = Template(f.read())
        component = t.safe_substitute(os.environ)
        return comp.load_component_from_text(component)
