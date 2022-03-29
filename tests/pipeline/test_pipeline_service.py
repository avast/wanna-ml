import os
import shutil
import unittest
from pathlib import Path

import pandas as pd
from google import auth
from google.cloud import aiplatform
from google.cloud.aiplatform.pipeline_jobs import PipelineJob
from mock import patch
from mock.mock import MagicMock

from tests.mocks import mocks
from wanna.cli.docker.service import DockerService
from wanna.cli.models.docker import ImageBuildType, LocalBuildImageModel, ProvidedImageModel
from wanna.cli.plugins.pipeline.service import PipelineService
from wanna.cli.utils.config_loader import load_config_from_yaml


@patch(
    "wanna.cli.utils.gcp.gcp.ZonesClient",
    mocks.MockZonesClient,
)
@patch(
    "wanna.cli.utils.gcp.gcp.RegionsClient",
    mocks.MockRegionsClient,
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
        shutil.rmtree(self.pipeline_build_dir, ignore_errors=True)

    def test_run_pipeline(self):
        # Setup Service
        config = load_config_from_yaml(self.sample_pipeline_dir / "wanna.yaml")
        pipeline_service = PipelineService(config=config, workdir=self.sample_pipeline_dir, version="test")

        # Setup expected data/fixtures
        expected_train_docker_image_model = LocalBuildImageModel(
            name="train",
            build_type=ImageBuildType.local_build_image,
            build_args=None,
            context_dir=".",
            dockerfile="Dockerfile.train",
        )
        expected_train_docker_tags = [
            "eu.gcr.io/us-burger-gcp-poc/pipeline-sklearn-example-1/train:test",
            "eu.gcr.io/us-burger-gcp-poc/pipeline-sklearn-example-1/train:latest",
        ]
        expected_serve_docker_image_model = ProvidedImageModel(
            name="serve",
            build_type=ImageBuildType.provided_image,
            image_url="europe-docker.pkg.dev/vertex-ai/prediction/xgboost-cpu.1-4:latest",
        )
        expected_serve_docker_tags = ["europe-docker.pkg.dev/vertex-ai/prediction/xgboost-cpu.1-4:latest"]

        # Check expected metadata
        expected_compile_env_params = {
            "project_id": "us-burger-gcp-poc",
            "pipeline_name": "wanna-sklearn-sample",
            "bucket": "gs://wanna-ml",
            "region": "europe-west4",
            # "pipeline_job_id": f"pipeline-wanna-sklearn-sample}-{get_timestamp()}", # TODO: make get_timestamp factory
            "pipeline_root": "gs://wanna-ml/pipeline-root/wanna-sklearn-sample",
            "pipeline_labels": """{"wanna_project": "pipeline-sklearn-example-1", "wanna_project_version": "1", """
            """"wanna_project_authors": "joao-silva1"}""",
        }
        expected_parameter_values = {"eval_acc_threshold": 0.87}
        expected_images = [
            (expected_train_docker_image_model, expected_train_docker_tags[0]),
            (expected_serve_docker_image_model, expected_serve_docker_tags[0]),
        ]
        expected_json_spec_path = self.pipeline_build_dir / "pipelines" / "wanna-sklearn-sample" / "pipeline_spec.json"

        # Mock Docker IO
        DockerService._find_image_model_by_ref = MagicMock(return_value=expected_train_docker_image_model)
        DockerService.build_image = MagicMock(return_value=None)
        DockerService.push_image = MagicMock(return_value=None)

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

        # Get compile result metadata
        pipelines = pipeline_service.compile("wanna-sklearn-sample")
        pipeline_meta = pipelines[0]

        # DockerService.build_image.assert_called_with(image_model=expected_train_docker_image_model,
        #                                              tags=expected_train_docker_tags)
        DockerService.build_image.assert_called_with(image_model=expected_serve_docker_image_model, tags=[])

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

        # Run pipeline on Vertex AI(Mocked GCP Calls)
        # Passing dummy callback as pipeline_job.state can't be mocked
        pipeline_service.run(pipelines, sync=True, exit_callback=lambda x, y: None)

        # Test GCP services were called and with correct args
        # pipeline_jobs.PipelineJob.assert_called_once()
        PipelineJob.submit.assert_called_once()
        PipelineJob.wait.assert_called_once()
        PipelineJob._dashboard_uri.assert_called_once()

        aiplatform.get_pipeline_df.assert_called_once()
        aiplatform.get_pipeline_df.assert_called_with(pipeline="wanna-sklearn-sample")
