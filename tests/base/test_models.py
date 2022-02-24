from wanna.cli.plugins.base.models import BaseInstanceModel
from pydantic.error_wrappers import ValidationError
from tests.mocks import mocks
import pytest


def test_model_project_id_start_with_number():
    with pytest.raises(ValidationError) as e_info:
        model = BaseInstanceModel.parse_obj(
            {"name": "my-model", "project_id": "34project"}
        )


def test_model_project_id_too_short():
    with pytest.raises(ValidationError) as e_info:
        model = BaseInstanceModel.parse_obj({"name": "my-model", "project_id": "pr"})


def test_model_project_too_long():
    with pytest.raises(ValidationError) as e_info:
        model = BaseInstanceModel.parse_obj(
            {"name": "my-model", "project_id": "a" * 60}
        )


def test_model_zone_not_existing(mocker):
    mocker.patch(
        "wanna.cli.utils.gcp.gcp.ZonesClient",
        mocks.MockZonesClient,
    )
    with pytest.raises(ValidationError) as e_info:
        model = BaseInstanceModel.parse_obj(
            {"name": "my-model", "project_id": "us-burger-gcp-poc", "zone": "cheap"}
        )


def test_model_zone_input_is_region_not_zone(mocker):
    mocker.patch(
        "wanna.cli.utils.gcp.gcp.ZonesClient",
        mocks.MockZonesClient,
    )
    with pytest.raises(ValidationError) as e_info:
        model = BaseInstanceModel.parse_obj(
            {
                "name": "my-model",
                "project_id": "us-burger-gcp-poc",
                "zone": "europe-west1",
            }
        )


def test_model_region_not_existing(mocker):
    mocker.patch(
        "wanna.cli.utils.gcp.gcp.RegionsClient",
        mocks.MockRegionsClient,
    )
    with pytest.raises(ValidationError) as e_info:
        model = BaseInstanceModel.parse_obj(
            {
                "name": "my-model",
                "project_id": "us-burger-gcp-poc",
                "region": "atlantida-cheap",
            }
        )
