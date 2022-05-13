import os
from pathlib import Path
from typing import Union

import kfp.components as comp


def load_wanna_component(path: Union[Path, str]):
    with open(str(path), "r") as f:
        component = os.path.expandvars(f.read())
        return comp.load_component_from_text(component)
