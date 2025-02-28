import logging
import re

from cron_validator import CronValidator
from google.api_core import exceptions
from google.cloud.notebooks_v1.types.instance import Instance
from google.cloud.storage import Client as StorageClient
from pydantic_core.core_schema import ValidationInfo

from wanna.core.models.docker import DockerModel
from wanna.core.utils.credentials import get_credentials
from wanna.core.utils.env import should_validate
from wanna.core.utils.gcp import (
    get_available_compute_machine_types,
    get_available_regions,
    get_available_zones,
    get_network_info,
)


def validate_docker_images_defined(value, info: ValidationInfo):
    docker_image_ref = info.data.get("environment", {}).get("docker_image_ref")
    if docker_image_ref:
        if not info.data.get("docker"):
            raise ValueError(f"Docker image with name {docker_image_ref} is not defined")
        docker_configuration: DockerModel | None = info.data.get("docker")
        defined_images = (
            [i.name for i in docker_configuration.images] if docker_configuration else []
        )
        if docker_image_ref not in defined_images:
            raise ValueError(f"Docker image with name {docker_image_ref} is not defined")
    return value


def validate_zone(zone, values):
    available_zones = get_available_zones(project_id=values.data.get("project_id"))
    if zone not in available_zones:
        raise ValueError(f"Zone invalid ({zone}). must be on of: {available_zones}")
    return zone


def validate_region(region, values):
    available_regions = get_available_regions(project_id=values.data.get("project_id"))
    if region not in available_regions:
        raise ValueError(f"Region invalid ({region}). must be on of: {available_regions}")
    return region


def validate_machine_type(machine_type, values):
    available_machine_types = get_available_compute_machine_types(
        project_id=values.data.get("project_id"), zone=values.data.get("zone")
    )
    if machine_type not in available_machine_types:
        raise ValueError(
            f"Machine type invalid ({machine_type}). must be on of: {available_machine_types}"
        )
    return machine_type


def validate_network_name(network_name: str | None):
    if network_name and not get_network_info(network_name):
        if not re.match("^[a-z][a-z0-9-]+$", network_name):
            raise ValueError(
                "Invalid format of network name. Either use the full name of VPC network"
                "'projects/{project_id}/global/networks/{network_id}'"
                "or just '{network_id}'. In the second case, the project_id will be parsed from notebook settings."
            )
    return network_name


def validate_bucket_name(bucket_name):
    if should_validate:
        try:
            _ = StorageClient(credentials=get_credentials()).get_bucket(bucket_name)
        except exceptions.NotFound:
            raise ValueError(f"Bucket with name {bucket_name} does not exist")
        except exceptions.Forbidden:
            logging.warning(f"Your user does not have permission to access bucket {bucket_name}")

    return bucket_name


def validate_only_one_must_be_set(cls, v):  # noqa: ARG001
    items_set = {key for key, value in v.items() if value is not None}
    if len(items_set) == 0:
        raise ValueError(f"One of {list(v.keys())} must be set.")
    elif len(items_set) > 1:
        raise ValueError(f"Specify only one of {items_set}")
    return v


def validate_cron_schedule(schedule: str):
    if schedule is not None and CronValidator.parse(schedule) is None:
        raise ValueError(f"Cron expression is invalid ({schedule}).")
    else:
        return schedule


def validate_disk_type(disk_type):
    disk_type = disk_type.upper()
    if disk_type not in Instance.DiskType.__members__:
        raise ValueError(
            f"Disk type invalid ({type}). must be on of: {Instance.DiskType._member_names_}"
        )
    return disk_type


def validate_accelerator_type(
    accelerator_type: Instance.AcceleratorType,
) -> Instance.AcceleratorType:
    if accelerator_type not in Instance.AcceleratorType.__members__:
        raise ValueError(
            f"GPU accelerator type invalid ({accelerator_type})."
            f"must be on of: {Instance.AcceleratorType._member_names_}"
        )
    return accelerator_type


def validate_project_id(project_id: str) -> str:
    if not re.match("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", project_id):
        raise ValueError(
            "Invalid GCP project id. project_id: "
            "Must be 6 to 30 characters in length. "
            "Contains lowercase letters, numbers, and hyphens. "
            "Must start with a letter. "
            "Cannot end with a hyphen."
        )
    return project_id


def validate_labels(labels: dict[str, str]) -> dict[str, str]:
    if not labels:
        return {}

    for key, value in labels.items():
        if not re.match(r"^[a-z]{1}[a-z0-9_-]{0,62}$", key) or not re.match(
            r"^[a-z0-9_-]{0,63}$", value
        ):
            raise ValueError(
                "Invalid custom label!"
                "Keys and values can contain only lowercase letters, numeric characters,"
                "underscores, and dashes. Max length is 63 characters."
                "https://cloud.google.com/compute/docs/labeling-resources#requirements"
            )
    return labels
