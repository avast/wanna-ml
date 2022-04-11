from mock import patch

from tests.mocks import mocks
from wanna.cli.models.tensorboard import TensorboardModel
from wanna.cli.models.wanna_config import WannaConfigModel
from wanna.cli.plugins.tensorboard.service import TensorboardService


@patch(
    "wanna.cli.utils.gcp.gcp.RegionsClient",
    mocks.MockRegionsClient,
)
class TestTensorboardService:
    def test_find_tensorboard_by_display_name(self, mocker):
        tb_service = TensorboardService(config=get_config())
        mocker.patch.object(
            tb_service,
            "_list_running_instances",
            mocks.mock_list_running_instances,
        )
        tb = TensorboardModel.parse_obj({"name": "tb1", "project_id": "gcp-project", "region": "europe-west4"})
        found = tb_service._find_existing_tensorboard_by_model(instance=tb)
        assert found is not None, ""
        tb = TensorboardModel.parse_obj({"name": "tb13", "project_id": "gcp-project", "region": "europe-west4"})
        found = tb_service._find_existing_tensorboard_by_model(instance=tb)
        assert found is None, ""


def get_config():
    return WannaConfigModel.parse_obj(
        {
            "wanna_project": {
                "name": "the-leaky-couldron",
                "version": "1.2.3",
                "authors": [
                    "bellatrix.lestrange@avast.com",
                    "fleaur.delacour@avast.com",
                ],
            },
            "gcp_profile": {"profile_name": "default", "project_id": "gcp-project", "zone": "us-east1-a"},
        }
    )
