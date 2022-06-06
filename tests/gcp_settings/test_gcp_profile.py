import os
from unittest import mock

import pytest
from mock import patch

from tests.mocks import mocks
from wanna.cli.models.gcp_settings import GCPProfileModel
from wanna.cli.utils.config_loader import load_config_from_yaml


@patch("wanna.cli.utils.gcp.gcp.ZonesClient", mocks.MockZonesClient)
@patch("wanna.cli.utils.gcp.gcp.RegionsClient", mocks.MockRegionsClient)
@patch("wanna.cli.utils.gcp.validators.StorageClient", mocks.MockStorageClient)
@patch("wanna.cli.utils.gcp.gcp.MachineTypesClient", mocks.MockMachineTypesClient)
@patch("wanna.cli.utils.gcp.gcp.ImagesClient", mocks.MockImagesClient)
@patch("wanna.cli.utils.gcp.validators.get_credentials", mocks.mock_get_credentials)
@patch("wanna.cli.utils.gcp.gcp.get_credentials", mocks.mock_get_credentials)
@patch("wanna.cli.utils.config_loader.get_credentials", mocks.mock_get_credentials)
@patch("wanna.cli.utils.io.get_credentials", mocks.mock_get_credentials)
class TestWannaConfigModel:
    def test_parse_region_from_zone(self):
        gcp_settings_dict = {"project_id": "gcp-project", "zone": "europe-west1-b", "profile_name": "default"}
        gcp_settings = GCPProfileModel.parse_obj(gcp_settings_dict)
        assert gcp_settings.region == "europe-west1"

    def test_load_profile_profile_name_set(self):
        config = load_config_from_yaml("samples/notebook/custom-container/wanna.yaml", "default")
        assert config.gcp_profile.zone == "europe-west1-b"
        assert config.gcp_profile.profile_name == "default"
        assert config.gcp_profile.bucket == "wanna-ml"

        config = load_config_from_yaml("samples/notebook/custom-container/wanna.yaml", "test")
        assert config.gcp_profile.zone == "europe-west4-a"
        assert config.gcp_profile.profile_name == "test"
        assert config.gcp_profile.bucket == "wanna-ml-test"

    def test_load_profile_invalid_profile_name(self):
        with pytest.raises(ValueError):
            load_config_from_yaml("samples/notebook/custom-container/wanna.yaml", "non-existing")

    @mock.patch.dict(os.environ, {"WANNA_GCP_PROFILE_PATH": "samples/notebook/custom-container/profiles.yaml"})
    def test_load_profile_from_env_path(self):
        config = load_config_from_yaml("samples/notebook/custom-container/wanna.yaml", "prod")
        assert config.gcp_profile.profile_name == "prod"
        assert config.gcp_profile.bucket == "wanna-ml-prod"
        os.environ["WANNA_GCP_PROFILE_PATH"] = ""