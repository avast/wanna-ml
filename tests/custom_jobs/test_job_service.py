from pathlib import Path

from google import auth
from google.cloud.aiplatform_v1.types.pipeline_state import PipelineState
from mock import MagicMock, patch

from tests.mocks import mocks
from wanna.cli.plugins.job.service import JobService
from wanna.cli.utils.config_loader import load_config_from_yaml


@patch(
    "wanna.cli.utils.gcp.gcp.RegionsClient",
    mocks.MockRegionsClient,
)
@patch(
    "wanna.cli.utils.gcp.gcp.MachineTypesClient",
    mocks.MockMachineTypesClient,
)
@patch(
    "wanna.cli.utils.gcp.gcp.ImagesClient",
    mocks.MockImagesClient,
)
@patch(
    "wanna.cli.utils.gcp.gcp.ZonesClient",
    mocks.MockZonesClient,
)
class TestJobService:
    @patch("wanna.cli.docker.service.docker")
    def test_create_training_job_spec_python_package_spec(self, docker_mock):
        auth.default = MagicMock(
            return_value=(
                None,
                None,
            )
        )
        config = load_config_from_yaml("samples/custom_job/wanna.yaml", "default")
        service = JobService(config=config, workdir=Path("."))
        job_model = service.instances[0]
        # Mock Docker IO
        docker_mock.build = MagicMock(return_value=None)
        docker_mock.pull = MagicMock(return_value=None)
        worker_spec = service._create_training_job_manifest(job_model)

        assert worker_spec.__dict__.get("_container_uri") == "gcr.io/cloud-aiplatform/training/tf-gpu.2-1:latest"
        assert worker_spec.__dict__.get("_python_module") == "trainer.task"

    @patch("wanna.cli.docker.service.docker")
    def test_create_worker_pool_spec_container_spec(self, docker_mock):
        auth.default = MagicMock(
            return_value=(
                None,
                None,
            )
        )
        config = load_config_from_yaml("samples/custom_job/wanna.yaml", "default")
        service = JobService(config=config, workdir=Path("."))
        job_model = service.instances[1]
        # Mock Docker IO
        docker_mock.build = MagicMock(return_value=None)
        docker_mock.pull = MagicMock(return_value=None)
        worker_spec = service._create_training_job_manifest(job_model)

        assert worker_spec.__dict__.get("_container_uri") == "gcr.io/google-containers/debian-base:1.0.0"
        assert worker_spec.__dict__.get("_command") == ["echo", "'Test'"]

    def test_list_job_filter(self):
        auth.default = MagicMock(
            return_value=(
                None,
                None,
            )
        )
        config = load_config_from_yaml("samples/custom_job/wanna.yaml", "default")
        service = JobService(config=config, workdir=Path("."))
        filter_expr_complete = service._create_list_jobs_filter_expr(
            states=[
                PipelineState.PIPELINE_STATE_PAUSED,
                PipelineState.PIPELINE_STATE_RUNNING,
                PipelineState.PIPELINE_STATE_FAILED,
            ],
            job_name="123",
        )
        assert (
            filter_expr_complete
            == '(state="PIPELINE_STATE_PAUSED" OR state="PIPELINE_STATE_RUNNING" OR state="PIPELINE_STATE_FAILED") AND '
            'display_name="123"'
        )

        filter_expr_no_job_name = service._create_list_jobs_filter_expr(
            states=[
                PipelineState.PIPELINE_STATE_PAUSED,
                PipelineState.PIPELINE_STATE_RUNNING,
                PipelineState.PIPELINE_STATE_FAILED,
            ]
        )
        assert (
            filter_expr_no_job_name
            == '(state="PIPELINE_STATE_PAUSED" OR state="PIPELINE_STATE_RUNNING" OR state="PIPELINE_STATE_FAILED")'
        )

        filter_expr_one_state = service._create_list_jobs_filter_expr(states=[PipelineState.PIPELINE_STATE_PAUSED])
        assert filter_expr_one_state == '(state="PIPELINE_STATE_PAUSED")'
