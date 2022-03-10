from pathlib import Path
from typing import Any, Dict, TextIO

import marshmallow_dataclass
import yaml
from yamlinclude import YamlIncludeConstructor

from wanna.cli.plugins.models import WannaFile


def load_yaml(stream: TextIO, context_dir: Path, **extras: Any) -> Dict[Any, Any]:
    """
    Convert a YAML stream into a class via the OrderedLoader class.
    """
    YamlIncludeConstructor.add_to_loader_class(loader_class=yaml.FullLoader, base_dir=context_dir)
    yaml_dict = yaml.load(stream, Loader=yaml.FullLoader) or {}
    yaml_dict.update(extras)
    return yaml_dict


def dump_dict_yaml(component_dict: any):
    class CustomDumper(yaml.Dumper):
        # Super neat hack to preserve the mapping key order. See https://stackoverflow.com/a/52621703/1497385
        def represent_dict_preserve_order(self, data):
            return self.represent_dict(data.items())

    CustomDumper.add_representer(dict, CustomDumper.represent_dict_preserve_order)

    return yaml.dump(component_dict, Dumper=CustomDumper)


def load_wanna(project_file: Path, project_dir: Path) -> WannaFile:
    with open(project_file) as f:
        # Load workflow file
        wanna_dict = load_yaml(f, project_dir)
        wanna_schema = marshmallow_dataclass.class_schema(WannaFile)()
        wanna_model: WannaFile = wanna_schema.load(wanna_dict)
        return wanna_model
