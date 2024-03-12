import os
import pathlib
from pathlib import Path
from typing import Any, Dict

from wanna.core.loggers.wanna_logger import get_logger
from wanna.core.models.gcp_profile import GCPProfileModel
from wanna.core.models.wanna_config import WannaConfigModel
from wanna.core.utils import loaders
from wanna.core.utils.env import gcp_access_allowed

logger = get_logger(__name__)


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


def load_config_from_yaml(
    wanna_config_path: Path, gcp_profile_name: str
) -> WannaConfigModel:
    """
    Load the yaml file from wanna_config_path and parses the information to the models.
    This also includes the data validation.

    Args:
        wanna_config_path: path to the wanna-ml yaml file
        gcp_profile_name: name of the GCP profile
        profiles_file_path: optionally passed through cli

    Returns:
        WannaConfigModel

    """

    with logger.user_spinner("Reading and validating wanna yaml config"):
        with open(wanna_config_path) as file:
            # Load workflow file
            wanna_dict = loaders.load_yaml(
                file, pathlib.Path(wanna_config_path).parent.resolve()
            )
        profile_model = load_gcp_profile(
            profile_name=gcp_profile_name, wanna_dict=wanna_dict
        )
        os.environ["GOOGLE_CLOUD_PROJECT"] = profile_model.project_id
        wanna_dict.update({"gcp_profile": profile_model})
        del wanna_dict["gcp_profiles"]
        wanna_config = WannaConfigModel.parse_obj(wanna_dict)
    logger.user_info(f"GCP profile '{profile_model.profile_name}' will be used.")
    logger.user_info(f"Profile details: {profile_model}")

    if gcp_access_allowed:
        # doing this import here speeds up the CLI app considerably
        from google.cloud import aiplatform

        from wanna.core.utils.credentials import get_credentials

        aiplatform.init(
            project=wanna_config.gcp_profile.project_id,
            location=wanna_config.gcp_profile.region,
            credentials=get_credentials(),
        )

    return wanna_config
