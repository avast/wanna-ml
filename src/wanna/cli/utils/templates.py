from jinja2 import Template
from pathlib import Path


def render_template(source_path: Path, **kwargs) -> str:
    with open(source_path) as f:
        template = Template(f.read())
    return template.render(**kwargs)
