from mock import patch
from wanna.cli.models.gcp_settings import GCPSettingsModel

from tests.mocks import mocks


@patch(
    "wanna.cli.utils.gcp.gcp.ZonesClient",
    mocks.MockZonesClient,
)
@patch(
    "wanna.cli.utils.gcp.gcp.RegionsClient",
    mocks.MockRegionsClient,
)
class TestWannaConfigModel:
    def setup(self):
        self.gcp_settings_dict = {"project_id": "gcp-project", "zone": "us-east1-a"}

    def test_parse_region_from_zone(self):
        gcp_settings = GCPSettingsModel.parse_obj(self.gcp_settings_dict)
        assert gcp_settings.region == "us-east1"
