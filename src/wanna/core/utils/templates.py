import os
import sys
from pathlib import Path

from jinja2 import Template


def render_template(source_path: Path, **kwargs) -> str:
    templates_dir = Path(os.path.dirname(sys.modules["wanna.core"].__file__)) / "templates"  # type: ignore
    source_path = templates_dir / source_path
    with open(source_path) as f:
        template = Template(f.read())
    return template.render(**kwargs)
