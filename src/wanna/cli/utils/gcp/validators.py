import logging
import re
from google.api_core import exceptions
from google.cloud import storage
from google.cloud.notebooks_v1.types.instance import Instance
from wanna.cli.utils.gcp.gcp import (
    get_available_compute_image_families,
    get_available_compute_machine_types,
    get_available_zones,
    get_available_regions,
)


def validate_zone(zone, values):
    available_zones = get_available_zones(project_id=values.get("project_id"))
    if not zone in available_zones:
        raise ValueError(f"Zone invalid ({zone}). must be on of: {available_zones}")
    return zone


def validate_region(region, values):
    available_regions = get_available_regions(project_id=values.get("project_id"))
    if not region in available_regions:
        raise ValueError(f"Zone invalid ({region}). must be on of: {available_regions}")
    return region


def validate_machine_type(machine_type, values):
    available_machine_types = get_available_compute_machine_types(
        project_id=values.get("project_id"), zone=values.get("zone")
    )
    if not machine_type in available_machine_types:
        raise ValueError(
            f"Machine type invalid ({machine_type}). must be on of: {available_machine_types}"
        )
    return machine_type


def validate_requirements(cls, v):
    if not any(v.values()):
        raise ValueError(
            f"One of requirements.file (path to your requirements.txt) or requirements.package_list (list of pip packages to install) must be set if you want to install python packages with requirements block."
        )
    return v


def validate_network_name(network_name):
    if not re.match(
        "^(projects\/[a-z0-9-]+\/global\/networks\/[a-z0-9-]+)$", network_name
    ):
        if not re.match("^[a-z0-9-]+$", network_name):
            raise ValueError(
                "Invalid format of network name. Either use the full name of VPC network 'projects/{project_id}/global/networks/{network_id}'"
                "or just '{network_id}'. In the second case, the project_id will be parsed from notebook settings."
            )
    return network_name


def validate_bucket_name(bucket_name):
    try:
        exists = storage.Client().bucket(bucket_name).exists()
        if not exists:
            raise ValueError(f"Bucket with name {bucket_name} does not exist")
    except exceptions.Forbidden as e:
        logging.warning(
            f"Your user does not have permission to access bucket {bucket_name}"
        )
    return bucket_name


def validate_vm_image(cls, v):
    framework = v.get("framework")
    version = v.get("version")
    os = v.get("os")
    available_image_families = get_available_compute_image_families(
        project="deeplearning-platform-release",
        filter="(-deprecated:*)",
        family_must_contain="notebook",
    )
    available_frameworks = set(i.get("framework") for i in available_image_families)
    if not framework in available_frameworks:
        raise ValueError(
            f"VM Image framework {framework} not available. Choose one of: {available_frameworks}"
        )

    available_versions = set(
        i.get("version")
        for i in available_image_families
        if i.get("framework") == framework
    )
    if not version in available_versions:
        raise ValueError(
            f"VM Image version {version} not available for {framework}. Choose one of: {available_versions}"
        )

    if os:
        available_os = set(
            i.get("os")
            for i in available_image_families
            if i.get("framework") == framework and i.get("version") == version
        )
        if not os in available_os:
            raise ValueError(
                f"VM Image OS {os} not available for {framework} and version {version}. Choose one of: {available_os}"
            )

    return v


def validate_only_one_must_be_set(cls, v):
    items_set = {key for key, value in v.items() if value is not None}
    if len(items_set) == 0:
        raise ValueError(f"One of {list(v.keys())} must be set.")
    elif len(items_set) > 1:
        raise ValueError(f"Specify only one of {items_set}")
    return v


def validate_disk_type(disk_type):
    disk_type = disk_type.upper()
    if not disk_type in Instance.DiskType.__members__:
        raise ValueError(
            f"GPU accelerator type invalid ({type}). must be on of: {Instance.DiskType._member_names_}"
        )
    return disk_type


def validate_accelerator_type(accelerator_type):
    if not accelerator_type in Instance.AcceleratorType.__members__:
        raise ValueError(
            f"GPU accelerator type invalid ({accelerator_type}). must be on of: {Instance.AcceleratorType._member_names_}"
        )
    return accelerator_type


def validate_project_id(project_id):
    if not re.match("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", project_id):
        raise ValueError(
            "Invalid GCP project id. project_id: "
            "Must be 6 to 30 characters in length. "
            "Contains lowercase letters, numbers, and hyphens. "
            "Must start with a letter. "
            "Cannot end with a hyphen."
        )
    return project_id
