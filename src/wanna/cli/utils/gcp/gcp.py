from google.cloud.compute import MachineTypesClient, ZonesClient
from google.cloud.compute_v1.services.images import ImagesClient
from google.cloud.compute_v1.types import ListImagesRequest
from google.cloud import storage
import re


def get_available_compute_machine_types(project: str, zone: str) -> list:
    response = MachineTypesClient().list(project=project, zone=zone)
    return [mtype.name for mtype in response.items]


def get_available_zones(project_id: str) -> list:
    response = ZonesClient().list(project=project_id)
    return [zone.name for zone in response.items]


def parse_image_name_family(name):
    framework = name.partition("-")[0]
    version = re.search("(?<=-)(.*?)(?=-notebooks)", name).group()
    os = None if name.endswith("notebooks") else name.split("-notebooks-")[-1]
    return {"framework": framework, "version": version, "os": os}


def get_available_compute_image_families(
    project: str, filter: str = None, family_must_contain: str = None
) -> list:
    list_images_request = ListImagesRequest(project=project, filter=filter)
    all_images = ImagesClient().list(list_images_request)
    if family_must_contain:
        return [
            parse_image_name_family(image.family)
            for image in all_images
            if family_must_contain in image.family
        ]
    return [parse_image_name_family(image.family) for image in all_images]


def upload_file_to_gcs(
    filename: str, bucket_name: str, blob_name: str
) -> storage.blob.Blob:
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(filename)
    return blob


def upload_string_to_gcs(
    data: str, bucket_name: str, blob_name: str
) -> storage.blob.Blob:
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(data)
    return blob
