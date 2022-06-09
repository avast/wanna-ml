from pathlib import Path
from typing import Any, Dict, TextIO

import yaml
from yamlinclude import YamlIncludeConstructor


def load_yaml(stream: TextIO, context_dir: Path, **extras: Any) -> Dict[Any, Any]:
    """
    Convert a YAML stream into a class via the OrderedLoader class.
    """
    YamlIncludeConstructor.add_to_loader_class(loader_class=yaml.FullLoader, base_dir=context_dir)
    yaml_dict = yaml.load(stream, Loader=yaml.FullLoader) or {}
    yaml_dict.update(extras)
    return yaml_dict


def load_yaml_path(path: Path, context_dir: Path, **extras: Any) -> Dict[Any, Any]:
    """
    Convert a Path into a yaml dict
    """
    with open(path, "r") as f:
        return load_yaml(f, context_dir, **extras)
