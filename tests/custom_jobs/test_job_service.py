from pathlib import Path

from google import auth
from google.cloud.aiplatform_v1.types.pipeline_state import PipelineState
from mock import MagicMock, patch

from wanna.core.services.jobs import JobService
from wanna.core.services.tensorboard import TensorboardService
from wanna.core.utils.config_loader import load_config_from_yaml


class TestJobService:
    @patch("wanna.core.services.docker.docker")
    def test_create_training_job_manifest_python_package_spec(self, docker_mock):
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
        # Mock Tensorboard Service
        TensorboardService.get_or_create_tensorboard_instance_by_name = MagicMock(return_value="some-tf-board")

        job_manifest = service._create_training_job_resource(job_model)
        assert job_manifest.job_payload.get("container_uri") == "gcr.io/cloud-aiplatform/training/tf-gpu.2-1:latest"
        assert job_manifest.job_payload.get("python_module_name") == "trainer.task"

    @patch("wanna.core.services.docker.docker")
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
        manifest = service._create_training_job_resource(job_model)

        assert manifest.job_payload.get("container_uri") == "gcr.io/google-containers/debian-base:1.0.0"
        assert manifest.job_payload.get("command") == ["echo", "'Test'"]

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
