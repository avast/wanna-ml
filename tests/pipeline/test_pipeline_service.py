import copy
import os
import shutil
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path

from google import auth
from google.cloud import aiplatform, logging, scheduler_v1
from google.cloud.aiplatform.pipeline_jobs import PipelineJob
from google.cloud.functions_v1.services.cloud_functions_service import (
    CloudFunctionsServiceClient,
)
from google.cloud.monitoring_v3 import (
    AlertPolicyServiceClient,
    NotificationChannel,
    NotificationChannelServiceClient,
)
from google.cloud.pubsub_v1 import PublisherClient
from mock import patch
from mock.mock import MagicMock, call

import wanna.core.services.pipeline
from wanna.core.deployment.models import (
    ContainerArtifact,
    JsonArtifact,
    PathArtifact,
    PushMode,
)
from wanna.core.models.docker import (
    DockerBuildResult,
    ImageBuildType,
    LocalBuildImageModel,
)
from wanna.core.services.docker import DockerService
from wanna.core.services.pipeline import PipelineService
from wanna.core.services.tensorboard import TensorboardService
from wanna.core.utils.config_loader import load_config_from_yaml


@dataclass
class DeploymentPaths:
    """Container for deployment artifact paths."""

    release_path: Path
    latest_release_path: Path
    manifest_path: Path
    latest_manifest_path: Path
    manifest_json_path: str
    latest_manifest_json_path: str
    pipeline_spec_path: str


def create_deployment_paths(base_path: Path, version: str) -> DeploymentPaths:
    """
    Create deployment artifact paths for a pipeline.

    Args:
        base_path: Base directory path for deployment manifests
        version: Version identifier (e.g. "test")

    Returns:
        DeploymentPaths object containing all relevant paths
    """
    release_path = base_path / version
    latest_release_path = base_path / "latest"

    manifest_path = release_path / "manifests"
    latest_manifest_path = latest_release_path / "manifests"

    manifest_json_path = str(manifest_path / "wanna-manifest.json")
    latest_manifest_json_path = str(latest_manifest_path / "wanna-manifest.json")
    pipeline_spec_path = str(manifest_path / "pipeline-spec.json")

    return DeploymentPaths(
        release_path=release_path,
        latest_release_path=latest_release_path,
        manifest_path=manifest_path,
        latest_manifest_path=latest_manifest_path,
        manifest_json_path=manifest_json_path,
        latest_manifest_json_path=latest_manifest_json_path,
        pipeline_spec_path=pipeline_spec_path,
    )


class TestPipelineService(unittest.TestCase):
    maxDiff = None
    parent = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
    test_runner_dir = parent / ".build" / "test_pipeline_service"
    sample_pipeline_dir = parent / "samples" / "pipelines" / "sklearn"
    test_pipeline_params_override_dir = sample_pipeline_dir / "params.test.yaml"
    pipeline_build_dir = sample_pipeline_dir / "build"

    # Add sample_pipeline_dir to Python path to simulate the usage of venv containing the sample project
    sys.path.insert(0, str(sample_pipeline_dir.absolute()))

    def setUp(self) -> None:
        self.project_id = "gcp-project"
        self.zone = "us-east1-a"
        shutil.rmtree(self.pipeline_build_dir, ignore_errors=True)
        self.test_runner_dir.mkdir(parents=True, exist_ok=True)
        auth.default = MagicMock(
            return_value=(
                None,
                None,
            )
        )

    def tearDown(self) -> None:
        pass

    @patch("wanna.core.services.docker.docker")
    def test_run_pipeline(self, docker_mock):
        docker_mock.build = MagicMock(return_value=None)
        docker_mock.pull = MagicMock(return_value=None)

        config = load_config_from_yaml(self.sample_pipeline_dir / "wanna.yaml", "default")
        pipeline_service = PipelineService(
            config=config, workdir=self.sample_pipeline_dir, version="test"
        )
        # Setup expected data/fixtures
        expected_train_docker_image_model = LocalBuildImageModel(
            name="train",
            build_type=ImageBuildType.local_build_image,
            build_args=None,
            context_dir=".",
            dockerfile="Dockerfile.train",
        )
        expected_train_docker_tags = [
            "europe-west1-docker.pkg.dev/your-gcp-project-id/wanna-samples/pipeline-sklearn-example-1/train:test",
            "europe-west1-docker.pkg.dev/your-gcp-project-id/wanna-samples/pipeline-sklearn-example-1/train:latest",
        ]
        expected_serve_docker_tags = [
            "europe-docker.pkg.dev/vertex-ai/prediction/xgboost-cpu.1-4:latest"
        ]
        exppected_pipeline_root = (
            "gs://your-staging-bucket-name/wanna-pipelines/wanna-sklearn-sample/executions/"
        )

        expected_pipeline_labels = (
            """{"wanna_project": "pipeline-sklearn-example-1", """
            """"wanna_project_version": "1", "wanna_project_authors": "jane-doe", "author": "jane-doe", """
            """"wanna_resource_name": "wanna-sklearn-sample", "wanna_resource": "pipeline"}"""
        )

        # Check expected metadata
        expected_compile_env_params = {
            "project_id": "your-gcp-project-id",
            "pipeline_name": "wanna-sklearn-sample",
            "bucket": "gs://your-staging-bucket-name",
            "region": "europe-west1",
            "version": "test",
            "pipeline_root": exppected_pipeline_root,
            "pipeline_labels": expected_pipeline_labels,
            "tensorboard": "projects/123456789/locations/europe-west4/tensorboards/123456789",
            "pipeline_network": "projects/123456789/global/networks/default",
            "pipeline_service_account": "wanna-dev@your-gcp-project-id.iam.gserviceaccount.com",
            "encryption_spec_key_name": "projects/project_id/locations/region/keyRings/key_ring/cryptoKeys/key",
            "pipeline_experiment": "wanna-sample-experiment",
        }

        expected_parameter_values = {
            "eval_acc_threshold": 0.95,
            "start_date": """{{ modules.pendulum.now().in_timezone('UTC').subtract(days=1).format('YYYY/MM/DD') }}""",
            "model_path": "gs://my-bucket/wanna-jobs/a/outputs/xgb_model.pkl",
        }
        expected_images = [
            DockerBuildResult(
                name="train",
                tags=[expected_train_docker_tags[0]],
                build_type=ImageBuildType.local_build_image,
            ),
            DockerBuildResult(
                name="serve",
                tags=expected_serve_docker_tags,
                build_type=ImageBuildType.provided_image,
            ),
        ]
        expected_json_spec_path = (
            self.pipeline_build_dir
            / "wanna-pipelines"
            / "wanna-sklearn-sample"
            / "deployment"
            / "test"
            / "manifests"
            / "pipeline-spec.json"
        )
        expected_json_spec_eval_path = (
            self.pipeline_build_dir
            / "wanna-pipelines"
            / "wanna-sklearn-sample-eval"
            / "deployment"
            / "test"
            / "manifests"
            / "pipeline-spec.json"
        )

        # Mock PipelineService
        PipelineService._make_pipeline_root = MagicMock(return_value=exppected_pipeline_root)
        TensorboardService.get_or_create_tensorboard_instance_by_name = MagicMock(
            return_value="projects/123456789/locations/europe-west4/tensorboards/123456789"
        )

        # Mock Docker IO
        DockerService._find_image_model_by_name = MagicMock(
            return_value=expected_train_docker_image_model
        )
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

        # === Build ===
        # Get compile result metadata
        pipelines = pipeline_service.build(
            instance_name="all",
            pipeline_params_path=self.test_pipeline_params_override_dir,
        )
        manifest_path, manifest_eval_path = pipelines
        pipeline_meta = PipelineService.read_manifest(
            pipeline_service.connector, str(manifest_path)
        )
        pipeline_eval_meta = PipelineService.read_manifest(
            pipeline_service.connector, str(manifest_eval_path)
        )

        docker_mock.build.assert_called_with(
            self.sample_pipeline_dir,
            file=self.sample_pipeline_dir / expected_train_docker_image_model.dockerfile,
            tags=expected_train_docker_tags,
            load=True,
        )

        self.assertEqual(pipeline_meta.enable_caching, False)
        self.assertEqual(pipeline_meta.compile_env_params, expected_compile_env_params)
        self.assertEqual(Path(pipeline_meta.json_spec_path), expected_json_spec_path)
        self.assertEqual(pipeline_meta.parameter_values, expected_parameter_values)

        # asserting the non "latest" docker tag was created
        self.assertEqual(
            pipeline_meta.docker_refs,
            expected_images,  # for now we only want the one with version, not latest
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
        aiplatform.init = MagicMock(return_value=None)
        PipelineService.run([str(manifest_path)], sync=True)
        aiplatform.init.assert_called_once()

        # Test GCP services were called and with correct args
        # pipeline_jobs.PipelineJob.assert_called_once()
        PipelineJob.submit.assert_called_once()
        PipelineJob.wait.assert_called_once()
        PipelineJob._dashboard_uri.assert_called_once()

        # === Push ===
        DockerService.push_image = MagicMock(return_value=None)
        push_result = pipeline_service.push(pipelines, local=True)
        DockerService.push_image.assert_called_once()

        release_manifests_path = (
            self.pipeline_build_dir / "wanna-pipelines" / "wanna-sklearn-sample" / "deployment"
        )
        release_manifests_eval_path = (
            self.pipeline_build_dir
            / "wanna-pipelines"
            / "wanna-sklearn-sample-eval"
            / "deployment"
        )
        expected_train = create_deployment_paths(release_manifests_path, "test")
        expected_eval = create_deployment_paths(release_manifests_eval_path, "test")

        # Should have been updated to new pushed path
        pipeline_meta.json_spec_path = expected_train.pipeline_spec_path

        expected_push_result = [
            (
                [
                    ContainerArtifact(name="train", tags=[expected_train_docker_tags[0]]),
                ],
                [
                    PathArtifact(
                        name="Kubeflow V2 pipeline spec",
                        source=str(expected_json_spec_path),
                        destination=expected_train.pipeline_spec_path,
                    ),
                ],
                [
                    JsonArtifact(
                        name="WANNA pipeline manifest",
                        json_body=pipeline_meta.model_dump(),
                        destination=expected_train.manifest_json_path,
                    ),
                    JsonArtifact(
                        name="WANNA pipeline manifest",
                        json_body=pipeline_meta.model_dump(),
                        destination=expected_train.latest_manifest_json_path,
                    ),
                ],
            ),
            (
                [],
                [
                    PathArtifact(
                        name="Kubeflow V2 pipeline spec",
                        source=str(expected_json_spec_eval_path),
                        destination=expected_eval.pipeline_spec_path,
                    ),
                ],
                [
                    JsonArtifact(
                        name="WANNA pipeline manifest",
                        json_body=pipeline_eval_meta.model_dump(),
                        destination=expected_eval.manifest_json_path,
                    ),
                    JsonArtifact(
                        name="WANNA pipeline manifest",
                        json_body=pipeline_eval_meta.model_dump(),
                        destination=expected_eval.latest_manifest_json_path,
                    ),
                ],
            ),
        ]

        self.assertEqual(push_result, expected_push_result)
        self.assertTrue(os.path.exists(expected_train.pipeline_spec_path))
        self.assertTrue(os.path.exists(expected_eval.pipeline_spec_path))
        self.assertTrue(os.path.exists(expected_train.manifest_json_path))
        self.assertTrue(os.path.exists(expected_eval.manifest_json_path))
        self.assertTrue(os.path.exists(expected_train.latest_manifest_json_path))
        self.assertTrue(os.path.exists(expected_eval.latest_manifest_json_path))

        # === Deploy ===
        parent = "projects/your-gcp-project-id/locations/europe-west1"
        local_cloud_functions_package = expected_train.release_path / "functions" / "package.zip"
        copied_cloud_functions_package = (
            "gs://your-staging-bucket-name/"
            "wanna-pipelines/wanna-sklearn-sample/deployment/test/functions/package.zip"
        )
        copied_cloud_functions_eval_package = (
            "gs://your-staging-bucket-name/"
            "wanna-pipelines/wanna-sklearn-sample-eval/deployment/test/functions/package.zip"
        )

        expected_function_name = "wanna-sklearn-sample-local"
        expected_function_name_resoure = f"{parent}/functions/{expected_function_name}"
        expected_function_url = "https://europe-west1-your-gcp-project-id.cloudfunctions.net/wanna-sklearn-sample-local"
        expected_function = {
            "name": expected_function_name_resoure,
            "description": "wanna wanna-sklearn-sample function for local pipeline",
            "source_archive_url": copied_cloud_functions_package,
            "entry_point": "process_request",
            "runtime": "python39",
            "https_trigger": {
                "url": expected_function_url,
            },
            "service_account_email": "wanna-dev@your-gcp-project-id.iam.gserviceaccount.com",
            "labels": {
                "wanna_project": "pipeline-sklearn-example-1",
                "wanna_project_version": "1",
                "wanna_project_authors": "jane-doe",
                "author": "jane-doe",
                "wanna_resource_name": "wanna-sklearn-sample",
                "wanna_resource": "pipeline",
            },
            "environment_variables": {
                "PROJECT_ID": "your-gcp-project-id",
                "PIPELINE_NAME": "wanna-sklearn-sample",
                "VERSION": "test",
                "BUCKET": "gs://your-staging-bucket-name",
                "REGION": "europe-west1",
                "PIPELINE_ROOT": "gs://your-staging-bucket-name/wanna-pipelines/wanna-sklearn-sample/executions/",
                "PIPELINE_LABELS": expected_pipeline_labels,
                "PIPELINE_NETWORK": "projects/123456789/global/networks/default",
                "PIPELINE_SERVICE_ACCOUNT": "wanna-dev@your-gcp-project-id.iam.gserviceaccount.com",
                "TENSORBOARD": "projects/123456789/locations/europe-west4/tensorboards/123456789",
                "ENCRYPTION_SPEC_KEY_NAME": "projects/project_id/locations/region/keyRings/key_ring/cryptoKeys/key",
                "PIPELINE_EXPERIMENT": "wanna-sample-experiment",
            },
            "available_memory_mb": 512,
        }
        expected_function_eval = copy.deepcopy(expected_function)
        expected_function_eval["source_archive_url"] = copied_cloud_functions_eval_package

        # Set Mocks
        NotificationChannelServiceClient.list_notification_channels = MagicMock(return_value=[])
        NotificationChannelServiceClient.create_notification_channel = MagicMock(
            return_value=NotificationChannel(
                name="projects/[PROJECT_ID_OR_NUMBER]/notificationChannels/[CHANNEL_ID]"
            )
        )
        AlertPolicyServiceClient.list_alert_policies = MagicMock(return_value=[])
        AlertPolicyServiceClient.update_alert_policy = MagicMock()
        AlertPolicyServiceClient.create_alert_policy = MagicMock()

        logging.Client.metrics_api.metric_create = MagicMock()
        logging.Client.metrics_api.metric_get = MagicMock()

        PublisherClient.get_topic = MagicMock()

        CloudFunctionsServiceClient.get_function = MagicMock()
        CloudFunctionsServiceClient.update_function = MagicMock()
        scheduler_v1.CloudSchedulerClient.get_job = MagicMock()
        scheduler_v1.CloudSchedulerClient.update_job = MagicMock()
        scheduler_v1.CloudSchedulerClient.update_job = MagicMock()
        wanna.core.services.path_utils.PipelinePaths.get_gcs_wanna_manifest_path = MagicMock(
            return_value=expected_train.manifest_json_path
        )

        # Deploy the thing
        pipeline_service.deploy("all", env="local")

        # Check cloud functions packaged was copied to pipeline-root
        self.assertTrue(os.path.exists(local_cloud_functions_package))

        # Check pubsub topic existence was checked
        PublisherClient.get_topic.assert_has_calls(
            [
                call(
                    topic="projects/your-gcp-project-id/topics/wanna-sample-pipeline-pubsub-channel"
                ),
                call(
                    topic="projects/your-gcp-project-id/topics/wanna-sample-pipeline-pubsub-channel"
                ),
            ]
        )

        # Check cloudfunctions sdk methods were called with expected function params
        CloudFunctionsServiceClient.get_function.assert_has_calls(
            [
                call({"name": f"{parent}/functions/wanna-sklearn" "-sample-local"}),
                call({"name": f"{parent}/functions/wanna-sklearn" "-sample-local"}),
            ]
        )
        CloudFunctionsServiceClient.update_function.assert_has_calls(
            [
                call({"function": expected_function}),
                call().result(),
                call({"function": expected_function_eval}),
                call().result(),
            ]
        )
        NotificationChannelServiceClient.create_notification_channel.assert_called_with(
            name="projects/your-gcp-project-id",
            notification_channel=NotificationChannel(
                type_="pubsub",
                display_name="wanna-sample-pipeline-pubsub-channel-wanna-alert-topic-channel",
                labels={
                    "topic": "projects/your-gcp-project-id/topics/wanna-sample-pipeline-pubsub-channel"
                },
                user_labels={
                    "wanna_project": "pipeline-sklearn-example-1",
                    "wanna_project_version": "1",
                    "wanna_project_authors": "jane-doe",
                    "author": "jane-doe",
                    "wanna_resource_name": "wanna-sklearn-sample",
                    "wanna_resource": "pipeline",
                },
                verification_status=NotificationChannel.VerificationStatus.VERIFIED,
                enabled=True,
            ),
        )

        # Assert Cloud Scheduler calls
        expected_job_name = expected_function_name
        job_name = f"{parent}/jobs/{expected_job_name}"
        self.assertEqual(scheduler_v1.CloudSchedulerClient.get_job.call_count, 2)
        self.assertEqual(scheduler_v1.CloudSchedulerClient.update_job.call_count, 2)
        scheduler_v1.CloudSchedulerClient.get_job.assert_called_with({"name": job_name})

        self.assertEqual(AlertPolicyServiceClient.list_alert_policies.call_count, 6)
        self.assertEqual(AlertPolicyServiceClient.create_alert_policy.call_count, 6)

        push_network = pipeline_service._get_resource_network(
            project_id="test-project-id",
            push_mode=PushMode.all,
            resource_network="pipeline-network",
            fallback_project_network="fallback-network",
        )
        self.assertEqual(push_network, "projects/123456789/global/networks/pipeline-network")

        non_push_network = pipeline_service._get_resource_network(
            project_id="test-project-id",
            push_mode=PushMode.containers,
            resource_network=None,
            fallback_project_network="fallback-network",
        )

        self.assertEqual(
            non_push_network,
            "projects/test-project-id/global/networks/fallback-network",
        )
