import os
import unittest
from pathlib import Path

from wanna.core.services.path_utils import JobPaths


class TestJobService(unittest.TestCase):
    parent = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
    test_runner_dir = parent / "build" / "test_job"
    sample_job_dir = parent / "samples" / "custom_job"
    job_build_dir = sample_job_dir / "build"

    def setUp(self) -> None:
        self.job_paths = JobPaths(self.sample_job_dir, "gs://test_bucket", "custom-job-with-containers")
        self.version = "test"

    def test_job_paths(self) -> None:
        wanna_local_manifest_file = self.job_paths.get_local_job_wanna_manifest_path(self.version)
        wanna_gcs_manifest_file = self.job_paths.get_gcs_job_wanna_manifest_path(self.version)

        self.assertEqual(
            wanna_gcs_manifest_file,
            "gs://test_bucket/wanna-jobs/custom-job-with-containers/deployment/test/manifests/job-manifest.json",
        )
        self.assertEqual(
            wanna_local_manifest_file,
            str(
                self.job_build_dir
                / "wanna-jobs"
                / "custom-job-with-containers"
                / "deployment"
                / "test"
                / "manifests"
                / "job-manifest.json"
            ),
        )
