from google.cloud.aiplatform_v1.types.job_state import JobState
from mock import patch
from wanna.cli.models.training_custom_job import TrainingCustomJobModel
from wanna.cli.models.wanna_config import WannaConfigModel
from wanna.cli.plugins.job.service import JobService

from tests.mocks import mocks


@patch(
    "wanna.cli.utils.gcp.gcp.RegionsClient",
    mocks.MockRegionsClient,
)
class TestJobService:
    def test_create_worker_pool_spec_python_package_spec(self):
        service = JobService(config=get_config())
        job_model = TrainingCustomJobModel.parse_obj(get_job_info())
        worker_spec = service._create_worker_pool_spec(
            job_model.worker_pool_specs.worker
        )

        assert worker_spec.python_package_spec.executor_image_uri == "executor_image_a"
        assert worker_spec.python_package_spec.python_module == "python_module_1"
        assert not worker_spec.container_spec

    def test_create_worker_pool_spec_machine_spec(self):
        service = JobService(config=get_config())
        job_model = TrainingCustomJobModel.parse_obj(get_job_info())
        master_spec = service._create_worker_pool_spec(
            job_model.worker_pool_specs.master
        )

        assert master_spec.machine_spec.machine_type == "n1-standard-4"

    def test_create_worker_pool_spec_container_spec(self):
        service = JobService(config=get_config())
        job_model = TrainingCustomJobModel.parse_obj(get_job_info())
        master_spec = service._create_worker_pool_spec(
            job_model.worker_pool_specs.master
        )

        assert master_spec.container_spec.image_uri == "container_a"
        assert master_spec.container_spec.command[0] == "run training"

    def test_create_instance_request_scheduling(self):
        service = JobService(config=get_config())
        job_model = TrainingCustomJobModel.parse_obj(get_job_info())
        model_request = service._create_instance_request(job_model)

        assert model_request.scheduling.timeout.seconds == 60 * 60 * 12

    def test_create_instance_request_base_output_directory(self):
        service = JobService(config=get_config())
        job_model = TrainingCustomJobModel.parse_obj(get_job_info())
        model_request = service._create_instance_request(job_model)

        assert (
            model_request.base_output_directory.output_uri_prefix
            == "gs://my-bucket/my-model/outputs"
        )

    def test_create_instance_request_worker_pool_list(self):
        service = JobService(config=get_config())
        job_model = TrainingCustomJobModel.parse_obj(get_job_info())
        model_request = service._create_instance_request(job_model)

        assert len(model_request.worker_pool_specs) == 4
        assert (
            model_request.worker_pool_specs[0].container_spec.image_uri == "container_a"
        )
        assert model_request.worker_pool_specs[1].replica_count == 8
        assert model_request.worker_pool_specs[2].container_spec.args == [
            "reduction==true"
        ]
        assert not model_request.worker_pool_specs[3]

    def test_list_job_filter(self):
        service = JobService(config=get_config())
        filter_expr_complete = service._create_list_jobs_filter_expr(
            states=[
                JobState.JOB_STATE_PAUSED,
                JobState.JOB_STATE_RUNNING,
                JobState.JOB_STATE_FAILED,
            ],
            job_name="123",
        )
        assert (
            filter_expr_complete
            == '(state="JOB_STATE_PAUSED" OR state="JOB_STATE_RUNNING" OR state="JOB_STATE_FAILED") AND display_name="123"'
        )

        filter_expr_no_job_name = service._create_list_jobs_filter_expr(
            states=[
                JobState.JOB_STATE_PAUSED,
                JobState.JOB_STATE_RUNNING,
                JobState.JOB_STATE_FAILED,
            ]
        )
        assert (
            filter_expr_no_job_name
            == '(state="JOB_STATE_PAUSED" OR state="JOB_STATE_RUNNING" OR state="JOB_STATE_FAILED")'
        )

        filter_expr_one_state = service._create_list_jobs_filter_expr(
            states=[JobState.JOB_STATE_PAUSED]
        )
        assert filter_expr_one_state == '(state="JOB_STATE_PAUSED")'


def get_job_info() -> dict:
    return {
        "name": "job_a",
        "region": "europe-west4",
        "bucket": "my-bucket",
        "project_id": "gcp-project",
        "timeout_seconds": 60 * 60 * 12,
        "base_output_directory": "/my-model/outputs",
        "worker_pool_specs": {
            "reduction_server": {
                "container_spec": {
                    "image_uri": "container_b",
                    "args": ["reduction==true"],
                }
            },
            "master": {
                "container_spec": {
                    "image_uri": "container_a",
                    "command": ["run training"],
                },
                "machine_type": "n1-standard-4",
                "replica_count": 1,
            },
            "worker": {
                "python_package_spec": {
                    "executor_image_uri": "executor_image_a",
                    "package_uris": ["uri1", "uri2"],
                    "python_module": "python_module_1",
                },
                "replica_count": 8,
            },
        },
    }


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
            "gcp_settings": {"project_id": "gcp-project", "zone": "us-east1-a"},
        }
    )
