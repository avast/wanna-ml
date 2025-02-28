import os
import pathlib
import sys
from io import StringIO
from pathlib import Path
from typing import Any, ParamSpec, TypeVar

from wanna.core.loggers.wanna_logger import get_logger
from wanna.core.models.gcp_profile import GCPProfileModel
from wanna.core.models.wanna_config import WannaConfigModel
from wanna.core.models.wanna_project import WannaProjectModel
from wanna.core.utils import loaders
from wanna.core.utils.env import gcp_access_allowed
from wanna.core.utils.gcp import verify_gcloud_presence

logger = get_logger(__name__)


P = ParamSpec("P")
T = TypeVar("T")


def load_gcp_profile(profile_name: str, wanna_dict: dict[str, Any]) -> GCPProfileModel:
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
    profile_model = GCPProfileModel.model_validate(selected_profile)
    return profile_model


def load_config_from_yaml(
    wanna_config_path: Path | str, gcp_profile_name: str
) -> WannaConfigModel:
    """
    Load the yaml file from wanna_config_path and parses the information to the models.
    This also includes the data validation.

    Args:
        wanna_config_path: path to the wanna-ml yaml file
        gcp_profile_name: name of the GCP profile

    Returns:
        WannaConfigModel

    """
    wanna_config_path = (
        Path(wanna_config_path) if isinstance(wanna_config_path, str) else wanna_config_path
    )
    verify_gcloud_presence()
    with logger.user_spinner("Reading and validating wanna yaml config"):
        wanna_dict = load_yaml_maybe_stdin(wanna_config_path)

        # GCP Profile & Wanna Project metadata is required to be validated first, since are used as enrichers
        profile_model = load_gcp_profile(profile_name=gcp_profile_name, wanna_dict=wanna_dict)
        os.environ["GOOGLE_CLOUD_PROJECT"] = profile_model.project_id
        wanna_dict.update({"gcp_profile": profile_model})

        wanna_project = WannaProjectModel.model_validate(wanna_dict["wanna_project"])
        wanna_dict.update({"wanna_project": wanna_project})

        # Remove gcp_profiles from the dictionary
        del wanna_dict["gcp_profiles"]

        # Complete validation and metadata enrichment
        wanna_config = WannaConfigModel.model_validate(wanna_dict)

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


def load_yaml_maybe_stdin(wanna_config_path: Path) -> dict[str, Any]:
    """
    Loads yaml file from path or stdin if path is '-'

    Args:
        wanna_config_path: path to the yaml file or -

    Returns: loaded yaml

    """
    if str(wanna_config_path) == "-":
        return loaders.load_yaml(
            StringIO(sys.stdin.read()), pathlib.Path(wanna_config_path).parent.resolve()
        )
    else:
        with open(wanna_config_path, encoding="utf-8") as file:
            # Load workflow file
            return loaders.load_yaml(file, pathlib.Path(wanna_config_path).parent.resolve())
