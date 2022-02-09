from google.cloud.devtools.cloudbuild_v1.services.cloud_build import CloudBuildClient
from google.cloud.devtools.cloudbuild_v1.types import (
    Build,
    Source,
    BuildStep,
    StorageSource,
)
from google.cloud import storage
from typing import List
import tarfile
import os


class GCPCloudBuildClient:
    def __init__(
        self,
    ):
        self.cloud_build_client = CloudBuildClient()

    def tar_local_directory(self, output_filename: str, source_dir: str) -> None:
        with tarfile.open(output_filename, "w:gz") as tar:
            tar.add(source_dir, arcname=os.path.sep)

    def upload_file_to_gcs(
        self, filename: str, bucket_name: str, blob_name: str
    ) -> storage.blob.Blob:
        storage_client = storage.Client()
        bucket = storage_client.get_bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(filename)
        return blob

    def build_docker_image_from_gcs_file(
        self, blob: storage.blob.Blob, image_name: str, project_id: str
    ) -> List[str]:
        steps = BuildStep(
            name="gcr.io/cloud-builders/docker", args=["build", "-t", image_name, "."]
        )
        build = Build(
            source=Source(
                storage_source=StorageSource(bucket=blob.bucket.name, object_=blob.name)
            ),
            steps=[steps],
            images=[image_name],
        )
        res = self.cloud_build_client.create_build(project_id=project_id, build=build)
        return [image.name for image in res.result().results.images]

    def build_docker_image_from_local_dir(
        self, source_dir: str, image_name: str, project_id: str, bucket: str
    ) -> List[str]:
        tar_name = image_name.replace(".", "_").replace("/", "_") + ".tar.gz"
        self.tar_local_directory(tar_name, source_dir)
        blob = self.upload_file_to_gcs(tar_name, bucket, tar_name)
        image_names = self.build_docker_image_from_gcs_file(
            blob, image_name, project_id
        )
        return image_names
