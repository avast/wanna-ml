import atexit
import os
from pathlib import Path

from caseconverter import kebabcase
from google.cloud.aiplatform.compat.types import pipeline_state_v1 as gca_pipeline_state_v1
from google.cloud.aiplatform.pipeline_jobs import PipelineJob

from wanna.core.utils.gcp.gcp import is_gcs_path
from wanna.core.utils.spinners import Spinner


def _at_pipeline_exit(pipeline_name: str, pipeline_job: PipelineJob, sync: bool, spinner: Spinner) -> None:
    @atexit.register
    def stop_pipeline_job():
        if sync and pipeline_job and pipeline_job.state != gca_pipeline_state_v1.PipelineState.PIPELINE_STATE_SUCCEEDED:
            spinner.fail(
                "detected exit signal, "
                f"shutting down running pipeline {pipeline_name} "
                f"at {pipeline_job._dashboard_uri()}."
            )
            pipeline_job.wait()
            pipeline_job.cancel()


class PipelinePaths:

    json_spec_filename = "pipeline-spec.json"
    wanna_manifest_filename = "wanna-manifest.json"

    def __init__(self, workdir: Path, bucket: str, pipeline_name: str):
        self.pipeline_name = pipeline_name
        self.workdir = workdir
        self.bucket = bucket
        self.pipelines_dir = (workdir / "build").resolve()
        self.local_pipeline_path = self._get_pipeline_path(str(self.pipelines_dir), pipeline_name)
        self.gcs_pipeline_path = self._get_pipeline_path(self.bucket, pipeline_name)

    def _get_pipeline_path(self, base_path: str, pipeline_name: str):
        if not is_gcs_path(base_path):
            os.makedirs(base_path, exist_ok=True)
        return f"{base_path}/wanna-pipelines/{kebabcase(pipeline_name).lower()}"

    def _get_pipeline_deployment_path(self, base_path: str, version: str):
        path = f"{base_path}/deployment/{version}"
        if not is_gcs_path(path):
            os.makedirs(path, exist_ok=True)
        return path

    def _get_pipeline_manifests_path(self, base_path: str, version: str):
        path = f"{base_path}/deployment/{version}/manifests"
        if not is_gcs_path(path):
            os.makedirs(path, exist_ok=True)
        return path

    def get_local_pipeline_manifest_path(self, version: str):
        return self._get_pipeline_manifests_path(self.local_pipeline_path, version)

    def get_gcs_pipeline_manifest_path(self, version: str):
        return self._get_pipeline_manifests_path(self.gcs_pipeline_path, version)

    def get_local_pipeline_deployment_path(self, version: str):
        return self._get_pipeline_deployment_path(self.local_pipeline_path, version)

    def get_gcs_pipeline_deployment_path(self, version: str):
        return self._get_pipeline_deployment_path(self.gcs_pipeline_path, version)

    def get_local_pipeline_json_spec_path(self, version: str):
        return f"{self.get_local_pipeline_manifest_path(version)}/{self.json_spec_filename}"

    def get_gcs_pipeline_json_spec_path(self, version: str):
        return f"{self.get_gcs_pipeline_manifest_path(version)}/{self.json_spec_filename}"

    def get_local_wanna_manifest_path(self, version: str):
        return f"{self.get_local_pipeline_manifest_path(version)}/{self.wanna_manifest_filename}"

    def get_gcs_wanna_manifest_path(self, version: str):
        return f"{self.get_gcs_pipeline_manifest_path(version)}/{self.wanna_manifest_filename}"

    def get_gcs_pipeline_root(self):
        return f"{self.gcs_pipeline_path}/executions/"

    def get_local_pipeline_root(self):
        return f"{self.local_pipeline_path}/executions/"
