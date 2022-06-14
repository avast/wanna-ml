import os
from unittest import mock

import pytest

from wanna.core.models.gcp_profile import GCPProfileModel
from wanna.core.utils.config_loader import load_config_from_yaml


class TestWannaConfigModel:
    def test_parse_region_from_zone(self):
        gcp_settings_dict = {
            "project_id": "gcp-project",
            "zone": "europe-west1-b",
            "profile_name": "default",
            "bucket": "bucket",
            "network": "default",
        }
        gcp_settings = GCPProfileModel.parse_obj(gcp_settings_dict)
        assert gcp_settings.region == "europe-west1"

    def test_load_profile_profile_name_set(self):
        config = load_config_from_yaml("samples/notebook/custom_container/wanna.yaml", "default")
        assert config.gcp_profile.zone == "europe-west1-b"
        assert config.gcp_profile.profile_name == "default"
        assert config.gcp_profile.bucket == "wanna-cloudlab-europe-west1"

        config = load_config_from_yaml("samples/notebook/custom_container/wanna.yaml", "test")
        assert config.gcp_profile.zone == "europe-west4-a"
        assert config.gcp_profile.profile_name == "test"
        assert config.gcp_profile.bucket == "wanna-cloudlab-europe-west3"

    def test_load_profile_invalid_profile_name(self):
        with pytest.raises(ValueError):
            load_config_from_yaml("samples/notebook/custom_container/wanna.yaml", "non-existing")

    @mock.patch.dict(os.environ, {"WANNA_GCP_PROFILE_PATH": "samples/notebook/custom_container/profiles.yaml"})
    def test_load_profile_from_env_path(self):
        config = load_config_from_yaml("samples/notebook/custom_container/wanna.yaml", "prod")
        assert config.gcp_profile.profile_name == "prod"
        assert config.gcp_profile.bucket == "wanna-ml-prod"
        os.environ["WANNA_GCP_PROFILE_PATH"] = ""
