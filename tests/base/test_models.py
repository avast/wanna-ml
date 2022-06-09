import pytest
from mock import patch
from pydantic.error_wrappers import ValidationError

from tests.mocks import mocks
from wanna.core.models.base_instance import BaseInstanceModel


@patch("wanna.core.utils.gcp.gcp.ZonesClient", mocks.MockZonesClient)
@patch("wanna.core.utils.gcp.gcp.RegionsClient", mocks.MockRegionsClient)
@patch("wanna.core.utils.gcp.validators.get_credentials", mocks.mock_get_credentials)
@patch("wanna.core.utils.gcp.gcp.get_credentials", mocks.mock_get_credentials)
class TestBaseModel:
    def test_model_project_id_start_with_number(self):
        with pytest.raises(ValidationError):
            _ = BaseInstanceModel.parse_obj({"name": "my-model", "project_id": "34astronomy"})

    def test_model_project_id_too_short(self):
        with pytest.raises(ValidationError):
            _ = BaseInstanceModel.parse_obj({"name": "my-model", "project_id": "pr"})

    def test_model_project_too_long(self):
        with pytest.raises(ValidationError):
            _ = BaseInstanceModel.parse_obj({"name": "my-model", "project_id": "a" * 60})

    def test_model_zone_not_existing(self):
        with pytest.raises(ValidationError):
            _ = BaseInstanceModel.parse_obj({"name": "my-model", "project_id": "gcp-project", "zone": "the-burrow"})

    def test_model_zone_input_is_region_not_zone(self):
        with pytest.raises(ValidationError):
            _ = BaseInstanceModel.parse_obj(
                {
                    "name": "my-model",
                    "project_id": "gcp-project",
                    "zone": "europe-west1",
                }
            )

    def test_model_region_not_existing(self):
        with pytest.raises(ValidationError):
            _ = BaseInstanceModel.parse_obj(
                {
                    "name": "my-model",
                    "project_id": "gcp-project",
                    "region": "atlantida-cheap",
                }
            )
