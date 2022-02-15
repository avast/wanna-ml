from google.cloud.compute import MachineTypesClient, ZonesClient
from google.cloud.compute_v1.services.images import ImagesClient
from google.cloud.compute_v1.types import ListImagesRequest
from google.cloud import storage
from typing import List, Dict
import re


def get_available_compute_machine_types(project_id: str, zone: str) -> List[str]:
    """
    Get available GCP Compute Engine Machine Types based on project and zone.
    Args:
        project (str): GCP project id
        zone (str): GCP project location (zone)

    Returns:
        list of available machine types
    """
    response = MachineTypesClient().list(project=project_id, zone=zone)
    return [mtype.name for mtype in response.items]


def get_available_zones(project_id: str) -> List[str]:
    """
    Get available GCP zones based on project.
    Args:
        project (str): GCP project id

    Returns:
        list of available zones
    """
    response = ZonesClient().list(project=project_id)
    return [zone.name for zone in response.items]


def parse_image_name_family(name) -> Dict:
    """
    Based on GCP Compute Engine VM Image name family (eg. tf2-2-7-cu113-notebooks-debian-10)
    return framework (eg. tf2), version (eg. 2-7-cu113), os (debian-10) information.

    Args:
        name: VM Image family name

    Returns:
        Dictionary with framework, version and os

    """
    framework = name.partition("-")[0]
    version = re.search("(?<=-)(.*?)(?=-notebooks)", name).group()
    os = None if name.endswith("notebooks") else name.split("-notebooks-")[-1]
    return {"framework": framework, "version": version, "os": os}


def get_available_compute_image_families(
    project_id: str, filter: str = None, family_must_contain: str = None
) -> List[Dict]:
    """
    List available Compute Engine VM image families.

    Args:
        project_id: GCP Project ID
        filter: filter for the images https://googleapis.dev/python/compute/latest/compute_v1/types.html#google.cloud.compute_v1.types.ListImagesRequest.filter
        family_must_contain: additional string that must be a part of the image family name for easier filtering
                                (eg. notebook to filter only the Vertex AI Workbench notebook-ready images)

    Returns:
        List of dicts from parse_image_name_family
    """
    list_images_request = ListImagesRequest(project=project_id, filter=filter)
    all_images = ImagesClient().list(list_images_request)
    if family_must_contain:
        return [
            parse_image_name_family(image.family)
            for image in all_images
            if family_must_contain in image.family
        ]
    return [parse_image_name_family(image.family) for image in all_images]


def construct_vm_image_family_from_vm_image(
    framework: str, version: str, os: str
) -> str:
    """
    Construct name of the Compute Engine VM family with given framework(eg. pytorch), version(eg. 1-9-xla)
    and optional OS (eg. debian-10).

    Args:
        framework (str): VM image framework (pytorch, r, tf2, ...)
        version (str): Version of the framework
        os (str): operation system

    Returns:
        object: Compute Engine VM Family name
    """
    if os:
        return f"{framework}-{version}-notebooks-{os}"
    else:
        return f"{framework}-{version}-notebooks"


def upload_file_to_gcs(
    filename: str, bucket_name: str, blob_name: str
) -> storage.blob.Blob:
    """
    Upload file to GCS bucket

    Args:
        filename (str): local file
        bucket_name (str):
        blob_name (str):

    Returns:
        storage.blob.Blob
    """
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(filename)
    return blob


def upload_string_to_gcs(
    data: str, bucket_name: str, blob_name: str
) -> storage.blob.Blob:
    """
    Upload a string to GCS bucket without saving it locally as a file.
    Args:
        data (str): string that will form a file on GCS
        bucket_name (str):
        blob_name (str):

    Returns:
        storage.blob.Blob
    """
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(data)
    return blob
