from mock import patch

from tests.mocks import mocks
from wanna.core.models.wanna_config import WannaConfigModel


@patch("wanna.cli.utils.gcp.gcp.MachineTypesClient", mocks.MockMachineTypesClient)
@patch("wanna.cli.utils.gcp.gcp.ImagesClient", mocks.MockImagesClient)
@patch("wanna.cli.utils.gcp.gcp.ZonesClient", mocks.MockZonesClient)
@patch("wanna.cli.utils.gcp.gcp.RegionsClient", mocks.MockRegionsClient)
@patch("wanna.cli.utils.gcp.validators.get_credentials", mocks.mock_get_credentials)
@patch("wanna.cli.utils.gcp.gcp.get_credentials", mocks.mock_get_credentials)
@patch("wanna.cli.utils.config_loader.get_credentials", mocks.mock_get_credentials)
@patch("wanna.cli.utils.io.get_credentials", mocks.mock_get_credentials)
class TestWannaConfigModel:
    def setup(self):
        self.wanna_config_dict = {
            "wanna_project": {
                "name": "hogwarts-owl",
                "version": "1.2.3",
                "authors": ["luna.lovegood@avast.com"],
            },
            "gcp_profile": {"profile_name": "default", "project_id": "gcp-project", "zone": "us-east1-a"},
            "notebooks": [
                {"name": "potions", "zone": "europe-west4-a", "labels": {"grade": "a"}},
                {"name": "history-of-magic"},
            ],
        }

    def test_labels_inheritance(self):
        wanna_config = WannaConfigModel.parse_obj(self.wanna_config_dict)
        assert wanna_config.notebooks[0].labels.get("grade") == "a"
        assert wanna_config.notebooks[0].labels.get("wanna_project") == "hogwarts-owl"
        assert wanna_config.notebooks[0].labels.get("wanna_project_authors") == "luna-lovegood"

    def test_parameters_propagation_dont_overwrite_if_exist(self):
        wanna_config = WannaConfigModel.parse_obj(self.wanna_config_dict)
        assert wanna_config.notebooks[0].zone == "europe-west4-a"

    def test_parameters_propagation_overwrite_if_not_exist(self):
        wanna_config = WannaConfigModel.parse_obj(self.wanna_config_dict)
        assert wanna_config.notebooks[1].zone == "us-east1-a"
