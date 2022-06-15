import os
import unittest
from pathlib import Path

from wanna.core.services.path_utils import PipelinePaths


class TestPipelineService(unittest.TestCase):
    parent = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
    test_runner_dir = parent / ".build" / "test_pipeline_service"
    sample_pipeline_dir = parent / "samples" / "pipelines" / "sklearn"
    pipeline_build_dir = sample_pipeline_dir / "build"

    def setUp(self) -> None:
        self.pipeline_paths = PipelinePaths(self.sample_pipeline_dir, "gs://test_bucket", "sklearn")
        self.version = "test"

    def test_gcs_paths(self) -> None:
        json_spec_file = self.pipeline_paths.get_gcs_pipeline_json_spec_path(self.version)
        wanna_manifest_file = self.pipeline_paths.get_gcs_wanna_manifest_path(self.version)
        pipeline_root = self.pipeline_paths.get_gcs_pipeline_root()

        self.assertEqual(
            json_spec_file, "gs://test_bucket/wanna-pipelines/sklearn/deployment/test/manifests/pipeline-spec.json"
        )
        self.assertEqual(
            wanna_manifest_file,
            "gs://test_bucket/wanna-pipelines/sklearn/deployment/test/manifests/wanna-manifest.json",
        )
        self.assertEqual(pipeline_root, "gs://test_bucket/wanna-pipelines/sklearn/executions/")

    def test_local_paths(self) -> None:
        json_spec_file = self.pipeline_paths.get_local_pipeline_json_spec_path(self.version)
        wanna_manifest_file = self.pipeline_paths.get_local_wanna_manifest_path(self.version)
        pipeline_root = self.pipeline_paths.get_local_pipeline_root()

        self.assertEqual(
            json_spec_file,
            str(self.pipeline_build_dir / "wanna-pipelines/sklearn/deployment/test/manifests/pipeline-spec.json"),
        )
        self.assertEqual(
            wanna_manifest_file,
            str(self.pipeline_build_dir / "wanna-pipelines/sklearn/deployment/test/manifests/wanna-manifest.json"),
        )
        self.assertEqual(pipeline_root, str(self.pipeline_build_dir / "wanna-pipelines/sklearn/executions") + "/")
