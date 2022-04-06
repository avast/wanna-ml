import os
import shutil
import unittest
from pathlib import Path

import pandas as pd
from google import auth
from google.cloud import aiplatform, scheduler_v1
from google.cloud.aiplatform.pipeline_jobs import PipelineJob
from google.cloud.functions_v1.services.cloud_functions_service import CloudFunctionsServiceClient
from mock import patch
from mock.mock import MagicMock

from tests.mocks import mocks
from wanna.cli.docker.service import DockerService
from wanna.cli.models.docker import ImageBuildType, LocalBuildImageModel, ProvidedImageModel
from wanna.cli.plugins.pipeline.service import PipelineService
from wanna.cli.plugins.tensorboard.service import TensorboardService
from wanna.cli.utils.config_loader import load_config_from_yaml


@patch(
    "wanna.cli.utils.gcp.gcp.ZonesClient",
    mocks.MockZonesClient,
)
@patch(
    "wanna.cli.utils.gcp.gcp.RegionsClient",
    mocks.MockRegionsClient,
)
@patch(
    "wanna.cli.utils.gcp.gcp.ImagesClient",
    mocks.MockImagesClient,
)
@patch(
    "wanna.cli.utils.gcp.gcp.MachineTypesClient",
    mocks.MockMachineTypesClient,
)
@patch(
    "wanna.cli.utils.gcp.validators.StorageClient",
    mocks.MockStorageClient,
)
class TestPipelineService(unittest.TestCase):
    parent = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
    test_runner_dir = parent / ".build" / "test_pipeline_service"
    sample_pipeline_dir = parent / "samples" / "pipelines" / "sklearn"
    pipeline_build_dir = sample_pipeline_dir / "build"

    def setup(self) -> None:
        self.project_id = "gcp-project"
        self.zone = "us-east1-a"
        shutil.rmtree(self.pipeline_build_dir, ignore_errors=True)
        self.test_runner_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        pass

    @patch("wanna.cli.docker.service.docker")
    def test_run_pipeline(self, docker_mock):
        # Setup Service
        config = load_config_from_yaml(self.sample_pipeline_dir / "wanna.yaml")
        pipeline_service = PipelineService(config=config, workdir=self.sample_pipeline_dir, version="test")
        print(pipeline_service.docker_service.image_store)
        # Setup expected data/fixtures
        expected_train_docker_image_model = LocalBuildImageModel(
            name="train",
            build_type=ImageBuildType.local_build_image,
            build_args=None,
            context_dir=".",
            dockerfile="Dockerfile.train",
        )
        expected_train_docker_tags = [
            "europe-west1-docker.pkg.dev/us-burger-gcp-poc/wanna-samples/pipeline-sklearn-example-1/train:test",
            "europe-west1-docker.pkg.dev/us-burger-gcp-poc/wanna-samples/pipeline-sklearn-example-1/train:latest",
        ]
        expected_serve_docker_image_model = ProvidedImageModel(
            name="serve",
            build_type=ImageBuildType.provided_image,
            image_url="europe-docker.pkg.dev/vertex-ai/prediction/xgboost-cpu.1-4:latest",
        )
        expected_serve_docker_tags = ["europe-docker.pkg.dev/vertex-ai/prediction/xgboost-cpu.1-4:latest"]
        exppected_pipeline_root = str(self.pipeline_build_dir / "pipelines" / "wanna-sklearn-sample" / "pipeline-root")
        os.makedirs(exppected_pipeline_root, exist_ok=True)

        # Check expected metadata
        expected_compile_env_params = {
            "project_id": "us-burger-gcp-poc",
            "pipeline_name": "wanna-sklearn-sample",
            "bucket": "gs://wanna-ml",
            "region": "europe-west1",
            "pipeline_root": exppected_pipeline_root,
            "pipeline_labels": """{"wanna_project": "pipeline-sklearn-example-1", "wanna_project_version": "1", """
            """"wanna_project_authors": "joao-silva1"}""",
            "tensorboard": "projects/123456789/locations/europe-west4/tensorboards/123456789",
        }
        expected_parameter_values = {"eval_acc_threshold": 0.87}
        expected_images = [
            (expected_train_docker_image_model, expected_train_docker_tags[0]),
            (expected_serve_docker_image_model, expected_serve_docker_tags[0]),
        ]
        expected_json_spec_path = self.pipeline_build_dir / "pipelines" / "wanna-sklearn-sample" / "pipeline_spec.json"

        # Mock PipelineService
        PipelineService._make_pipeline_root = MagicMock(return_value=exppected_pipeline_root)
        TensorboardService.get_or_create_tensorboard_instance_by_name = MagicMock(
            return_value="projects/123456789/locations/europe-west4/tensorboards/123456789"
        )

        # Mock Docker IO
        DockerService._find_image_model_by_name = MagicMock(return_value=expected_train_docker_image_model)
        docker_mock.build = MagicMock(return_value=None)
        docker_mock.pull = MagicMock(return_value=None)

        # Mock GCP calls
        auth.default = MagicMock(
            return_value=(
                None,
                None,
            )
        )
        PipelineJob.submit = MagicMock(return_value=None)
        PipelineJob.wait = MagicMock(return_value=None)
        PipelineJob._dashboard_uri = MagicMock(return_value=None)
        aiplatform.get_pipeline_df = MagicMock(return_value=pd.DataFrame(columns=["name"]))

        # === Build ===
        # Get compile result metadata
        pipelines = pipeline_service.build("wanna-sklearn-sample")
        (pipeline_meta, manifest_path) = pipelines[0]

        # DockerService.build_image.assert_called_with(image_model=expected_train_docker_image_model,
        #                                              tags=expected_train_docker_tags)
        docker_mock.build.assert_called_with(
            self.sample_pipeline_dir,
            file=self.sample_pipeline_dir / expected_train_docker_image_model.dockerfile,
            tags=expected_train_docker_tags,
        )

        del pipeline_meta.compile_env_params["pipeline_job_id"]  # TODO: make get_timestamp() factory

        self.assertEqual(pipeline_meta.config, config.pipelines[0])
        self.assertEqual(pipeline_meta.compile_env_params, expected_compile_env_params)
        self.assertEqual(pipeline_meta.json_spec_path, expected_json_spec_path)
        self.assertEqual(pipeline_meta.parameter_values, expected_parameter_values)

        # asserting the non "latest" docker tag was created
        self.assertEqual(
            [
                (
                    local,
                    tags,
                )
                for (local, _, tags) in pipeline_meta.images
            ],
            expected_images,
        )

        # Check expected env vars are set
        self.assertTrue(os.environ.get("WANNA_SKLEARN_SAMPLE_PIPELINE_NAME"))
        self.assertTrue(os.environ.get("WANNA_SKLEARN_SAMPLE_PIPELINE_ROOT"))
        self.assertTrue(os.environ.get("WANNA_SKLEARN_SAMPLE_REGION"))
        self.assertTrue(os.environ.get("WANNA_SKLEARN_SAMPLE_BUCKET"))
        self.assertTrue(os.environ.get("WANNA_SKLEARN_SAMPLE_PIPELINE_LABELS"))
        self.assertTrue(os.environ.get("TRAIN_DOCKER_URI"))
        self.assertTrue(os.environ.get("SERVE_DOCKER_URI"))

        # Check Kubeflow V2 pipelines json spec was created and exists
        self.assertTrue(expected_json_spec_path.exists())

        # === Run ===
        # Run pipeline on Vertex AI(Mocked GCP Calls)
        # Passing dummy callback as pipeline_job.state can't be mocked
        PipelineService.run([str(manifest_path)], sync=True, exit_callback=lambda x, y, z, i: None)

        # Test GCP services were called and with correct args
        # pipeline_jobs.PipelineJob.assert_called_once()
        PipelineJob.submit.assert_called_once()
        PipelineJob.wait.assert_called_once()
        PipelineJob._dashboard_uri.assert_called_once()

        aiplatform.get_pipeline_df.assert_called_once()
        aiplatform.get_pipeline_df.assert_called_with(pipeline="wanna-sklearn-sample")

        # === Push ===
        DockerService.push_image = MagicMock(return_value=None)
        pushed = pipeline_service.push(pipelines, version="dev", local=True)
        DockerService.push_image.assert_called_once()

        release_path = (
            self.pipeline_build_dir
            / "pipelines"
            / "wanna-sklearn-sample"
            / "pipeline-root"
            / "deployment"
            / "release"
            / "dev"
        )
        expected_manifest_json_path = str(release_path / "wanna_manifest.json")
        expected_pipeline_spec_path = str(release_path / "pipeline_spec.json")
        expected_push_result = [
            (
                expected_manifest_json_path,
                expected_pipeline_spec_path,
            )
        ]

        self.assertEqual(pushed, expected_push_result)
        self.assertTrue(os.path.exists(expected_pipeline_spec_path))
        self.assertTrue(os.path.exists(expected_manifest_json_path))

        # === Deploy ===
        parent = "projects/us-burger-gcp-poc/locations/europe-west1"
        local_cloud_functions_package = f"{release_path}/functions/package.zip"
        copied_cloud_functions_package = local_cloud_functions_package

        expected_function_name = "wanna-sklearn-sample-local"
        expected_function_name_resoure = f"{parent}/functions/{expected_function_name}"
        expected_function_url = "https://us-burger-gcp-poc-europe-west1.cloudfunctions.net/wanna-sklearn-sample-local"
        expected_function = {
            "name": expected_function_name_resoure,
            "description": "wanna wanna-sklearn-sample function for local pipeline",
            "source_archive_url": copied_cloud_functions_package,
            "entry_point": "process_request",
            "runtime": "python39",
            "https_trigger": {
                "url": expected_function_url,
            },
            "service_account_email": "wanna-ml-testing@us-burger-gcp-poc.iam.gserviceaccount.com",
            "labels": {
                "wanna_project": "pipeline-sklearn-example-1",
                "wanna_project_version": "1",
                "wanna_project_authors": "joao-silva1",
            },
        }

        # Set Mocks
        CloudFunctionsServiceClient.get_function = MagicMock()
        CloudFunctionsServiceClient.update_function = MagicMock()
        scheduler_v1.CloudSchedulerClient.get_job = MagicMock()
        scheduler_v1.CloudSchedulerClient.update_job = MagicMock()

        # Deploy the thing
        pipeline_service.deploy("all", version="dev", env="local")

        # Check cloud functions packaged was copied to pipeline-root
        self.assertTrue(os.path.exists(local_cloud_functions_package))

        # Check cloudfunctions sdk methos were called with expected function params
        CloudFunctionsServiceClient.get_function.assert_called_with(
            {"name": f"{parent}/functions/wanna-sklearn" "-sample-local"}
        )
        CloudFunctionsServiceClient.update_function.assert_called_with({"function": expected_function})

        # Assert Cloud Scheduler calls
        expected_job_name = expected_function_name
        job_name = f"{parent}/jobs/{expected_job_name}"
        scheduler_v1.CloudSchedulerClient.get_job.assert_called_once()
        scheduler_v1.CloudSchedulerClient.update_job.assert_called_once()
        scheduler_v1.CloudSchedulerClient.get_job.assert_called_with({"name": job_name})
        # scheduler_v1.CloudSchedulerClient.update_job.assert_called_with({})
