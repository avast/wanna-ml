from pathlib import Path
from typing import Any, Dict, TextIO

import yaml
from yamlinclude import YamlIncludeConstructor


def replace_environment_variables() -> None:
    """Enable yaml loader to process the environment variables in the yaml file."""
    import os
    import re

    # eg. ${USER_NAME}, ${PASSWORD}
    env_var_pattern = re.compile(r"^(.*)\$\{(.*)\}(.*)$")
    yaml.add_implicit_resolver("!env_var", env_var_pattern)

    def env_var_constructor(loader: Any, node: Any) -> Any:
        """Process environment variables found in the YAML."""
        value = loader.construct_scalar(node)
        return os.path.expandvars(value)

    yaml.add_constructor("!env_var", env_var_constructor)


def load_yaml(stream: TextIO, context_dir: Path, **extras: Any) -> Dict[Any, Any]:
    """
    Convert a YAML stream into a class via the OrderedLoader class.
    """
    YamlIncludeConstructor.add_to_loader_class(
        loader_class=yaml.FullLoader, base_dir=context_dir
    )
    replace_environment_variables()
    yaml_dict = yaml.load(stream, Loader=yaml.FullLoader) or {}
    yaml_dict.update(extras)
    return yaml_dict


def load_yaml_path(path: Path, context_dir: Path, **extras: Any) -> Dict[Any, Any]:
    """
    Convert a Path into a yaml dict
    """
    with open(path, "r") as f:
        return load_yaml(f, context_dir, **extras)
