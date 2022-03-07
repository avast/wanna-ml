from wanna.cli.models.tensorboard import TensorboardModel
from wanna.cli.plugins.tensorboard.service import TensorboardService
from wanna.cli.models.wanna_config import WannaConfigModel

from tests.mocks import mocks
from mock import patch


@patch(
    "wanna.cli.utils.gcp.gcp.RegionsClient",
    mocks.MockRegionsClient,
)
class TestTensorboardService:
    def __init__(self):
        self.config = WannaConfigModel.parse_obj(
            {
                "wanna_project": {
                    "name": "the-leaky-couldron",
                    "version": "1.2.3",
                    "authors": [
                        "bellatrix.lestrange@avast.com",
                        "fleaur.delacour@avast.com",
                    ],
                },
                "gcp_settings": {"project_id": "gcp-project", "zone": "us-east1-a"},
            }
        )

    def test_find_tensorboard_by_display_name(self, mocker):
        tb_service = TensorboardService(config=self.config)
        mocker.patch.object(
            tb_service,
            "_list_running_instances",
            mocks.mock_list_running_instances,
        )
        tb = TensorboardModel.parse_obj(
            {"name": "tb1", "project_id": "gcp-project", "region": "europe-west4"}
        )
        found = tb_service._find_tensorboard_by_display_name(instance=tb)
        assert found is not None, ""
        tb = TensorboardModel.parse_obj(
            {"name": "tb13", "project_id": "gcp-project", "region": "europe-west4"}
        )
        found = tb_service._find_tensorboard_by_display_name(instance=tb)
        assert found is None, ""
