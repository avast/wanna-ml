from pathlib import Path
from typing import Optional

from google.auth.credentials import Credentials
from google.cloud.aiplatform_v1.types import Tensorboard
from google.cloud.compute_v1.types import Image
from google.cloud.compute_v1.types.compute import (
    MachineType,
    MachineTypeList,
    Region,
    RegionList,
    Zone,
    ZoneList,
)
from google.cloud.notebooks_v2.types import (
    Instance,
    ListInstancesResponse,
    State,
)
from google.cloud.storage import Blob
from google.cloud.storage.bucket import Bucket


class MockZonesClient:
    def __init__(self, credentials: Optional[Credentials] = None):
        self.credentials = credentials

    def list(self, project: str):  # noqa: ARG002
        zone_names = ["europe-west4-a", "us-east1-a", "europe-west1-b"]
        return ZoneList(items=[Zone({"name": name}) for name in zone_names])


class MockRegionsClient:
    def __init__(self, credentials: Optional[Credentials] = None):
        self.credentials = credentials

    def list(self, project: str):  # noqa: ARG002
        region_names = ["europe-west1", "us-east1", "europe-west4"]
        return RegionList(items=[Region({"name": name}) for name in region_names])


class MockImagesClient:
    def __init__(self, credentials: Optional[Credentials] = None):
        self.credentials = credentials

    def list(self, list_images_request):  # noqa: ARG002
        image_families = [
            "tf2-ent-2-5-cu110-notebooks",
            "tf2-ent-2-5-cu110-notebooks-debian-10",
            "tf-ent-2-3-cpu-ubuntu-2004",
            "tf-ent-2-3-cu110-notebooks-ubuntu-1804",
            "tf-ent-2-3-cu110-notebooks",
        ]
        return [Image({"family": family}) for family in image_families]


class MockMachineTypesClient:
    def __init__(self, credentials: Optional[Credentials] = None):
        self.credentials = credentials

    def list(self, project: str, zone: str):  # noqa
        machine_type_names = [
            "n1-ultramem-160",
            "n2-highmem-96",
            "n2-standard-128",
            "n2d-standard-2",
            "n1-standard-4",
        ]
        return MachineTypeList(
            items=[MachineType({"name": mtype}) for mtype in machine_type_names]
        )


class MockStorageClient:
    def __init__(self, credentials: Optional[Credentials] = None):
        self.credentials = credentials

    def get_bucket(self, bucket_name: str):
        return Bucket(client=self, name=bucket_name)


def mock_get_credentials() -> Optional[Credentials]:
    return None


def mock_convert_project_id_to_project_number(project_id: str) -> int:  # noqa
    return 123456789


def mock_get_gcloud_user() -> str:
    return "jane-doe"


def mock_upload_file(any, src: str, dest: str):  # noqa
    return None


def upload_string_to_gcs(filename: Path, bucket_name: str, blob_name: str):  # noqa
    return Blob(blob_name, MockStorageClient().get_bucket(bucket_name))


def mock_list_running_instances(project_id: str, region: str):  # noqa
    tensorboard_names = ["tb1", "tb2"]
    return [
        Tensorboard(
            {
                "display_name": t,
            }
        )
        for t in tensorboard_names
    ]


class MockWorkbenchInstanceServiceClient:
    def __init__(self):
        self.notebook_states = {
            "nb1": State.ACTIVE,
            "tf-gpu": State.PROVISIONING,
            "pytorch-notebook": State.DELETED,
        }
        self.project_id = "gcp-project"
        self.zone = "us-east1-a"
        self.instances = [
            Instance(
                name=f"projects/{self.project_id}/locations/{self.zone}/instances/{n}",
                state=s,
            )
            for n, s in self.notebook_states.items()
        ]

    def list_instances(self, parent):
        return ListInstancesResponse(
            instances=[i for i in self.instances if i.name.startswith(parent)]
        )

    def get_instance(self, name):
        matched_instances = [i for i in self.instances if name == i.name]
        return matched_instances[0]


class MockVertexPipelinesMixInVertex:
    pass
