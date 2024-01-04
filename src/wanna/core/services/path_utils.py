import os
from pathlib import Path

from caseconverter import kebabcase


class JobPaths:
    job_manifest_filename = "job-manifest.json"

    def __init__(self, workdir: Path, bucket: str, job_name: str):
        self.pipeline_name = job_name
        self.workdir = workdir
        self.bucket = bucket
        self.pipelines_dir = (workdir / "build").resolve()
        self.local_job_path = self._get_local_job_path(self.pipelines_dir, job_name)
        self.gcs_job_path = self._get_gcs_job_path(self.bucket, job_name)

    def _get_local_job_path(self, base_path: Path, pipeline_name: str) -> Path:
        os.makedirs(base_path, exist_ok=True)
        return base_path / "wanna-jobs" / kebabcase(pipeline_name).lower()

    def _get_gcs_job_path(self, base_path: str, pipeline_name: str) -> str:
        return f"{base_path}/wanna-jobs/{kebabcase(pipeline_name).lower()}"

    def _get_local_job_manifests_path(self, base_path: Path, version: str) -> Path:
        path = base_path / "deployment" / version / "manifests"
        os.makedirs(path, exist_ok=True)
        return path

    def _get_gcs_job_manifests_path(self, base_path: str, version: str) -> str:
        path = f"{base_path}/deployment/{version}/manifests"
        return path

    def get_local_job_manifest_path(self, version: str) -> str:
        return str(self._get_local_job_manifests_path(self.local_job_path, version))

    def get_gcs_job_manifest_path(self, version: str) -> str:
        return self._get_gcs_job_manifests_path(self.gcs_job_path, version)

    def get_local_job_wanna_manifest_path(self, version: str) -> str:
        path = (
            Path(self.get_local_job_manifest_path(version)) / self.job_manifest_filename
        )
        return str(path)

    def get_gcs_job_wanna_manifest_path(self, version: str) -> str:
        return f"{self.get_gcs_job_manifest_path(version)}/{self.job_manifest_filename}"


class PipelinePaths:
    json_spec_filename = "pipeline-spec.json"
    wanna_manifest_filename = "wanna-manifest.json"
    job_manifest_filename = "job-manifest.json"

    def __init__(self, workdir: Path, bucket: str, pipeline_name: str):
        self.pipeline_name = pipeline_name
        self.workdir = workdir
        self.bucket = bucket
        self.pipelines_dir = (workdir / "build").resolve()
        self.local_pipeline_path = self._get_local_pipeline_path(
            self.pipelines_dir, pipeline_name
        )
        self.gcs_pipeline_path = self._get_gcs_pipeline_path(self.bucket, pipeline_name)
        self.local_job_path = self._get_local_pipeline_path(
            self.pipelines_dir, pipeline_name
        )
        self.gcs_job_path = self._get_gcs_pipeline_path(self.bucket, pipeline_name)

    def _get_local_pipeline_path(self, base_path: Path, pipeline_name: str) -> Path:
        os.makedirs(base_path, exist_ok=True)
        return base_path / "wanna-pipelines" / kebabcase(pipeline_name).lower()

    def _get_gcs_pipeline_path(self, base_path: str, pipeline_name: str) -> str:
        return f"{base_path}/wanna-pipelines/{kebabcase(pipeline_name).lower()}"

    def get_local_pipeline_manifest_path(self, version: str) -> str:
        path = self.local_pipeline_path / "deployment" / version / "manifests"
        os.makedirs(path, exist_ok=True)
        return str(path)

    def get_gcs_pipeline_manifest_path(self, version: str) -> str:
        path = f"{self.gcs_pipeline_path}/deployment/{version}/manifests"
        return path

    def get_local_pipeline_deployment_path(self, version: str) -> Path:
        path = self.local_pipeline_path / "deployment" / version
        os.makedirs(path, exist_ok=True)
        return path

    def get_gcs_pipeline_deployment_path(self, version: str) -> str:
        path = f"{self.gcs_pipeline_path}/deployment/{version}"
        return path

    def get_local_pipeline_json_spec_path(self, version: str) -> str:
        path = (
            Path(self.get_local_pipeline_manifest_path(version))
            / self.json_spec_filename
        )
        return str(path)

    def get_gcs_pipeline_json_spec_path(self, version: str) -> str:
        return (
            f"{self.get_gcs_pipeline_manifest_path(version)}/{self.json_spec_filename}"
        )

    def get_local_wanna_manifest_path(self, version: str) -> str:
        path = (
            Path(self.get_local_pipeline_manifest_path(version))
            / self.wanna_manifest_filename
        )
        return str(path)

    def get_gcs_wanna_manifest_path(self, version: str) -> str:
        return f"{self.get_gcs_pipeline_manifest_path(version)}/{self.wanna_manifest_filename}"

    def get_gcs_pipeline_root(self) -> str:
        return f"{self.gcs_pipeline_path}/executions/"

    def get_local_pipeline_root(self) -> str:
        path = self.local_pipeline_path / "executions"
        return str(path)
