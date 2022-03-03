from wanna.cli.models.tensorboard import TensorboardModel
from wanna.cli.plugins.tensorboard.service import TensorboardService

from tests.mocks import mocks


def test_find_tensorboard_by_display_name(mocker):
    mocker.patch(
        "wanna.cli.utils.gcp.gcp.RegionsClient",
        mocks.MockRegionsClient,
    )
    tb_service = TensorboardService()
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
