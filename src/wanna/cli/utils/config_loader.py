import os
import pathlib
from pathlib import Path
from typing import Any, Dict

from wanna.cli.models.gcp_settings import GCPProfileModel
from wanna.cli.models.wanna_config import WannaConfigModel
from wanna.cli.utils import loaders
from wanna.cli.utils.spinners import Spinner


def load_gcp_profile(profile_name: str, wanna_dict: Dict[str, Any]) -> GCPProfileModel:
    """
    This functions goes through wanna-ml config and optionally through a file
    $WANNA_GCP_PROFILE_PATH, reads all gcp profiles and returns the one
    with "profile_name" name

    Args:
        profile_name: name of the GCP profile
        wanna_dict: wanna-ml configuration as a dictionary

    Returns:
        GCPProfileModel
    """
    profiles = wanna_dict.get("gcp_profiles", {})
    profiles = {p.get("profile_name"): p for p in profiles}

    extra_profiles_path = os.getenv("WANNA_GCP_PROFILE_PATH")
    if extra_profiles_path and os.path.isfile(extra_profiles_path):
        extra_profiles = loaders.load_yaml_path(
            Path(extra_profiles_path), Path(extra_profiles_path).parent.absolute()
        ).get("gcp_profiles")
        if extra_profiles:
            extra_profiles = {p.get("profile_name"): p for p in extra_profiles}
            profiles.update(extra_profiles)

    if profile_name not in profiles:
        raise ValueError(f"Profile {profile_name} not found")

    selected_profile = profiles.get(profile_name)
    profile_model = GCPProfileModel.parse_obj(selected_profile)
    return profile_model


def load_config_from_yaml(wanna_config_path: Path, gcp_profile_name: str) -> WannaConfigModel:
    """
    Load the yaml file from wanna_config_path and parses the information to the models.
    This also includes the data validation.

    Args:
        wanna_config_path: path to the wanna-ml yaml file
        gcp_profile_name: name of the GCP profile

    Returns:
        WannaConfigModel
    """

    with Spinner(text="Reading and validating wanna yaml config"):
        with open(wanna_config_path) as file:
            # Load workflow file
            wanna_dict = loaders.load_yaml(file, pathlib.Path(wanna_config_path).parent.resolve())
        profile_model = load_gcp_profile(profile_name=gcp_profile_name, wanna_dict=wanna_dict)
        wanna_dict.update({"gcp_profile": profile_model})
        wanna_config = WannaConfigModel.parse_obj(wanna_dict)
    Spinner().info(f"GCP profile '{profile_model.profile_name}' will be used.\n" f"Profile details: {profile_model}")
    return wanna_config
