import pytest
from pydantic.error_wrappers import ValidationError

from wanna.core.models.base_instance import BaseInstanceModel


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
            _ = BaseInstanceModel.parse_obj(
                {"name": "my-model", "project_id": "gcp-project", "zone": "the-burrow"}
            )

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
