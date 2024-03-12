import os
import re
import tarfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from wanna.core.utils.env import should_validate

if should_validate:
    # since is very slow to import all these, we do it only when validation is required
    import google.auth
    from google.auth.exceptions import DefaultCredentialsError
    from google.cloud import storage
    from google.cloud.compute import MachineTypesClient, ZonesClient
    from google.cloud.compute_v1 import RegionsClient
    from google.cloud.compute_v1.services.images import ImagesClient
    from google.cloud.compute_v1.types import ListImagesRequest
    from google.cloud.resourcemanager_v3.services.projects import ProjectsClient

from wanna.core.utils.credentials import get_credentials

NETWORK_REGEX = (
    "projects/((?:(?:[-a-z0-9]{1,63}\\.)*(?:[a-z](?:[-a-z0-9]{0,61}[a-z0-9])?):)"
    "?(?:[0-9]{1,19}|(?:[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?)))/global/networks/"
    "((?:[a-z](?:[-a-z0-9]*[a-z0-9])?))$"
)


def are_gcp_credentials_set() -> bool:
    """
    Function to verify if the default GCP credentials can be abstracted
    from environment.

    Returns:
        True if GCP credentials can be found, False otherwise
    """
    try:
        _credentials, _project_id = google.auth.default()
        return True
    except DefaultCredentialsError:
        return False


def get_current_local_gcp_project_id() -> str:
    """
    Get current local GCP default project.

    Returns:
        project_id: your current local GCP default project
    """
    _, project_id = google.auth.default()
    return project_id


def get_available_compute_machine_types(project_id: str, zone: str) -> List[str]:
    """
    Get available GCP Compute Engine Machine Types based on project and zone.
    Args:
        project_id: GCP project id
        zone: GCP project location (zone)

    Returns:
        list of available machine types
    """
    if should_validate:
        response = MachineTypesClient(credentials=get_credentials()).list(
            project=project_id, zone=zone
        )
        machine_types = [mtype.name for mtype in response.items]
    else:
        machine_types = [
            "c2-standard-4",
            "c2-standard-8",
            "c2-standard-16",
            "c2-standard-30",
            "c2-standard-60",
            "e2-highcpu-2",
            "e2-highcpu-4",
            "e2-highcpu-8",
            "e2-highcpu-16",
            "e2-highcpu-32",
            "e2-highmem-2",
            "e2-highmem-4",
            "e2-highmem-8",
            "e2-highmem-16",
            "e2-medium",
            "e2-micro",
            "e2-small",
            "e2-standard-2",
            "e2-standard-4",
            "e2-standard-8",
            "e2-standard-16",
            "e2-standard-32",
            "f1-micro",
            "g1-small",
            "m1-megamem-96",
            "m1-ultramem-160",
            "m1-ultramem-40",
            "m1-ultramem-80",
            "m2-megamem-416",
            "m2-ultramem-208",
            "m2-ultramem-416",
            "n1-highcpu-2",
            "n1-highcpu-4",
            "n1-highcpu-8",
            "n1-highcpu-16",
            "n1-highcpu-32",
            "n1-highcpu-64",
            "n1-highcpu-96",
            "n1-highmem-16",
            "n1-highmem-2",
            "n1-highmem-4",
            "n1-highmem-8",
            "n1-highmem-32",
            "n1-highmem-64",
            "n1-highmem-96",
            "n1-megamem-96",
            "n1-standard-1",
            "n1-standard-2",
            "n1-standard-4",
            "n1-standard-8",
            "n1-standard-16",
            "n1-standard-32",
            "n1-standard-64",
            "n1-standard-96",
            "n1-ultramem-40",
            "n1-ultramem-80",
            "n1-ultramem-160",
            "n2-highcpu-2",
            "n2-highcpu-4",
            "n2-highcpu-8",
            "n2-highcpu-16",
            "n2-highcpu-32",
            "n2-highcpu-48",
            "n2-highcpu-64",
            "n2-highcpu-80",
            "n2-highcpu-96",
            "n2-highmem-2",
            "n2-highmem-4",
            "n2-highmem-8",
            "n2-highmem-16",
            "n2-highmem-32",
            "n2-highmem-48",
            "n2-highmem-64",
            "n2-highmem-80",
            "n2-highmem-96",
            "n2-highmem-128",
            "n2-standard-2",
            "n2-standard-4",
            "n2-standard-8",
            "n2-standard-16",
            "n2-standard-32",
            "n2-standard-48",
            "n2-standard-64",
            "n2-standard-80",
            "n2-standard-96",
            "n2-standard-128",
            "n2d-highcpu-128",
            "n2d-highcpu-2",
            "n2d-highcpu-4",
            "n2d-highcpu-8",
            "n2d-highcpu-16",
            "n2d-highcpu-32",
            "n2d-highcpu-48",
            "n2d-highcpu-64",
            "n2d-highcpu-80",
            "n2d-highcpu-96",
            "n2d-highcpu-224",
            "n2d-highmem-2",
            "n2d-highmem-4",
            "n2d-highmem-8",
            "n2d-highmem-16",
            "n2d-highmem-32",
            "n2d-highmem-48",
            "n2d-highmem-64",
            "n2d-highmem-80",
            "n2d-highmem-96",
            "n2d-standard-2",
            "n2d-standard-4",
            "n2d-standard-8",
            "n2d-standard-16",
            "n2d-standard-32",
            "n2d-standard-48",
            "n2d-standard-64",
            "n2d-standard-80",
            "n2d-standard-96",
            "n2d-standard-128",
            "n2d-standard-224",
            "t2d-standard-1",
            "t2d-standard-2",
            "t2d-standard-4",
            "t2d-standard-8",
            "t2d-standard-16",
            "t2d-standard-32",
            "t2d-standard-48",
            "t2d-standard-60",
            "a2-highgpu-1g",
            "a2-highgpu-2g",
            "a2-highgpu-4g",
            "a2-highgpu-8g",
            "a2-megagpu-16g",
        ]

    return machine_types


def get_available_zones(project_id: str) -> List[str]:
    """
    Get available GCP zones based on project.
    Args:
        project_id: GCP project id

    Returns:
        list of available zones
    """

    if should_validate:
        response = ZonesClient(credentials=get_credentials()).list(project=project_id)
        return [zone.name for zone in response.items]
    else:
        return [
            "us-east1-b",
            "us-east1-c",
            "us-east1-d",
            "us-west1-a",
            "us-west1-b",
            "us-west1-c",
            "europe-west1-b",
            "europe-west1-c",
            "europe-west1-d",
            "europe-west3-a",
            "europe-west3-b",
            "europe-west3-c",
            "europe-west4-a",
            "europe-west4-b",
            "europe-west4-c",
        ]


def get_available_regions(project_id: str) -> List[str]:
    """
    Get available GCP regions based on project.
    Args:
        project_id: GCP project id

    Returns:
        list of available regions
    """
    if should_validate:
        response = RegionsClient(credentials=get_credentials()).list(project=project_id)
        return [region.name for region in response.items]
    else:
        return ["europe-west1", "europe-west3", "europe-west4", "us-east1", "us-west1"]


def get_region_from_zone(zone: str) -> str:
    """
    Get available GCP region from zone.
    Args:
        zone: GCP zone

    Returns:
        region: GCP region
    """
    return zone.rpartition("-")[0]


def convert_project_id_to_project_number(project_id: str) -> str:
    """
    Convert GCP project_id (eg. 'my-gcp-project') to project_number (eg. '966193337054')

    Args:
        project_id: GCP project id

    Returns:
        project_number: GCP project number
    """
    project_name = (
        ProjectsClient(credentials=get_credentials())
        .get_project(name=f"projects/{project_id}")
        .name
    )
    project_number = re.sub("projects/", "", project_name)
    return project_number


def parse_image_name_family(name: str) -> Dict[str, Any]:
    """
    Based on GCP Compute Engine VM Image name family (eg. tf2-2-7-cu113-notebooks-debian-10)
    return framework (eg. tf2), version (eg. 2-7-cu113), os (debian-10) information.

    Args:
        name: VM Image family name

    Returns:
        Dictionary with framework, version and os

    """
    framework = name.partition("-")[0]
    match_version = re.search("(?<=-)(.*?)(?=-notebooks)", name)
    assert match_version is not None  # TODO: improve result assert with message
    version = match_version.group()
    os = None if name.endswith("notebooks") else name.split("-notebooks-")[-1]
    return {"framework": framework, "version": version, "os": os}


def get_available_compute_image_families(
    project: str,
    image_filter: Optional[str] = None,
    family_must_contain: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    List available Compute Engine VM image families.

    Args:
        project: VM Image project ID
        image_filter: filter for the images https://googleapis.dev/python/compute/latest/compute_v1/types.html#google.cloud.compute_v1.types.ListImagesRequest.filter
        family_must_contain: additional string that must be a part of the image family name for easier filtering
                                (eg. notebook to filter only the Vertex AI Workbench notebook-ready images)

    Returns:
        List of dicts from parse_image_name_family

    """  # noqa: E501
    list_images_request = ListImagesRequest(project=project, filter=image_filter)
    all_images = ImagesClient(credentials=get_credentials()).list(list_images_request)
    if family_must_contain:
        return [
            parse_image_name_family(image.family)
            for image in all_images
            if family_must_contain in image.family
        ]
    return [parse_image_name_family(image.family) for image in all_images]


def construct_vm_image_family_from_vm_image(
    framework: str, version: str, os: Optional[str]
) -> str:
    """
    Construct name of the Compute Engine VM family with given framework(eg. pytorch),
    version(eg. 1-9-xla) and optional OS (eg. debian-10).

    Args:
        framework: VM image framework (pytorch, r, tf2, ...)
        version: Version of the framework
        os: operation system

    Returns:
        object: Compute Engine VM Family name
    """
    if os:
        return f"{framework}-{version}-notebooks-{os}"
    return f"{framework}-{version}-notebooks"


def make_tarfile(source_dir: Path, output_filename: Path):
    """
    TAR a given folder and save the result to output_filename.

    Args:
        source_dir:
        output_filename:
    """
    os.makedirs(output_filename.parent.absolute(), exist_ok=True)
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=".")


def upload_file_to_gcs(
    filename: Path, bucket_name: str, blob_name: str
) -> "storage.blob.Blob":
    """
    Upload file to GCS bucket

    Args:
        filename: local file
        bucket_name:
        blob_name:

    Returns:
        storage.blob.Blob
    """
    storage_client = storage.Client(credentials=get_credentials())
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(filename)
    return blob


def upload_string_to_gcs(
    data: str, bucket_name: str, blob_name: str
) -> "storage.blob.Blob":
    """
    Upload a string to GCS bucket without saving it locally as a file.
    Args:
        data: string that will form a file on GCS
        bucket_name:
        blob_name:

    Returns:
        storage.blob.Blob
    """
    storage_client = storage.Client(credentials=get_credentials())
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(data)
    return blob


def is_gcs_path(path: str):
    """
    Simply checks if path str represents a GCS path
    Args:
        path: path string that will be checked

    Returns:
        bool
    """
    return path.startswith("gs://")


def get_network_info(network: Optional[str]) -> Optional[Tuple[str, str]]:
    """
    gets information about a network if set in long format
    Args:
        network: string to extract network info from
        bucket_name:
        blob_name:

    Returns:
        Tuple[str, str]
    """
    if network:
        result = re.search(NETWORK_REGEX, network)
        if result:
            return result.group(1), result.group(2)

    return None
