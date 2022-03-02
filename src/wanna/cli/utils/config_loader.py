from pathlib import Path
from wanna.cli.utils import loaders
from wanna.cli.models.wanna_config import WannaConfigModel
from wanna.cli.utils.spinners import Spinner


def load_config_from_yaml(wanna_config_path: Path) -> WannaConfigModel:
    """
    Load the yaml file from wanna_config_path and parses the information to the models.
    This also includes the data validation.

    Args:
        wanna_config_path: path to the wanna-ml yaml file
    """

    with Spinner(text="Reading and validating yaml config"):
        with open(wanna_config_path) as file:
            # Load workflow file
            wanna_dict = loaders.load_yaml(file, Path("."))
        wanna_config = WannaConfigModel.parse_obj(wanna_dict)
    return wanna_config
