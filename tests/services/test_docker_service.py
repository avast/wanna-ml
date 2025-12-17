import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from wanna.core.models.docker import DockerModel, ImageBuildType, LocalBuildImageModel
from wanna.core.models.gcp_profile import GCPProfileModel
from wanna.core.services.docker import DockerService


class TestDockerService(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        docker_model = DockerModel(
            registry="europe-west1-docker.pkg.dev",
            repository="test-repo",
            images=[
                LocalBuildImageModel(
                    name="test-image",
                    build_type=ImageBuildType.local_build_image,
                    dockerfile=Path("Dockerfile"),
                    context_dir=Path("."),
                )
            ],
        )
        gcp_profile = GCPProfileModel(
            profile_name="test-profile",
            project_id="test-project",
            region="europe-west1",
            bucket="test-bucket",
            docker_registry="europe-west1-docker.pkg.dev",
            docker_repository="test-repo",
        )
        self.docker_service = DockerService(
            docker_model=docker_model,
            gcp_profile=gcp_profile,
            version="test",
            work_dir=Path("."),
            wanna_project_name="test-project",
        )

    @patch("wanna.core.services.docker.gcloud_devtools_cloudbuild_v1_services_cloud_build")
    @patch("wanna.core.services.docker.get_credentials")
    @patch("wanna.core.services.docker.gapi_core_future_polling")
    @patch("wanna.core.services.docker.gprotobuf_duration_pb2")
    def test_build_image_on_gcp_cloud_build_method_signature(
        self,
        mock_duration_pb2,
        mock_polling,
        mock_get_credentials,
        mock_cloud_build_client,
    ):
        """Test that _build_image_on_gcp_cloud_build method can be called (lines 432-433)."""
        # Setup mocks
        mock_get_credentials.return_value = None

        # Mock Duration properly - return a real Duration-like object
        from google.protobuf.duration_pb2 import Duration

        mock_duration_pb2.Duration = Duration
        mock_polling.DEFAULT_POLLING._timeout = 3600

        mock_client = MagicMock()
        mock_operation = MagicMock()
        mock_operation.metadata.build.id = "build-123"
        mock_operation.result = MagicMock()
        mock_client.create_build.return_value = mock_operation
        mock_cloud_build_client.CloudBuildClient.return_value = mock_client

        # Mock the upload method
        mock_blob = MagicMock()
        mock_blob.bucket.name = "test-bucket"
        mock_blob.name = "test.tar.gz"
        self.docker_service._upload_context_dir_to_gcs = MagicMock(return_value=mock_blob)

        # Mock write checksum
        self.docker_service._write_context_dir_checksum = MagicMock()

        # Set cloud_build to True
        self.docker_service.cloud_build = True

        # Execute
        context_dir = Path("test_context")
        file_path = Path("Dockerfile")
        tags = ["test-image:test"]
        docker_image_ref = "test-image"

        self.docker_service._build_image_on_gcp_cloud_build(
            context_dir=context_dir,
            file_path=file_path,
            tags=tags,
            docker_image_ref=docker_image_ref,
        )

        # Verify CloudBuildClient was instantiated (method executed)
        mock_cloud_build_client.CloudBuildClient.assert_called_once()
        # Verify method signature was called (lines 432-433 executed)
        # The method successfully executed, which means the signature is correct

    @patch("wanna.core.services.docker.python_on_whales.docker.image.push")
    def test_push_image_method_signature(self, mock_push):
        """Test that push_image method can be called (lines 542-543)."""
        # Set cloud_build to False to enable push
        self.docker_service.cloud_build = False
        self.docker_service.overwrite_images = True

        # Mock remote_image_tag_exists
        self.docker_service.remote_image_tag_exists = MagicMock(return_value=False)

        # Execute with list of tags
        tags = ["test-image:test"]
        self.docker_service.push_image(image_or_tags=tags, quiet=False)

        # Verify push was called (method executed)
        mock_push.assert_called_once_with(tags[0], False)

    @patch("wanna.core.services.docker.python_on_whales.docker.image.push")
    def test_push_image_with_multiple_tags(self, mock_push):
        """Test push_image with multiple tags."""
        self.docker_service.cloud_build = False
        self.docker_service.overwrite_images = True
        self.docker_service.remote_image_tag_exists = MagicMock(return_value=False)

        # Execute with multiple tags
        tags = ["test-image:test", "test-image:latest"]
        self.docker_service.push_image(image_or_tags=tags, quiet=True)

        # Verify push was called for each tag
        assert mock_push.call_count == 2
