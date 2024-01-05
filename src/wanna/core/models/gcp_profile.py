from typing import Dict, Optional

from pydantic import BaseModel, Extra, root_validator, validator

from wanna.core.utils import validators
from wanna.core.utils.gcp import get_region_from_zone


class GCPProfileModel(BaseModel, extra=Extra.forbid):
    """
    `wanna_profile` section of the yaml config consists of the following inputs:

    - `profile_name` - [str] name of the WANNA GCP Profile, `default` will be used if not specified otherwise.
      You could use also for example `dev`, `prod`, or any other string.
    - `project_id` - [str] GCP project id.
    - `zone` - [str] (optional) GCP location zone.
    - `region` - [str] (optional) GCP location region. If the zone is set and the region not, we automatically
      parse the region from the zone (e.g., zone `us-east1-c` automatically sets region `us-east1` if the region
      is not supplied by the user).
    - `labels` - [Dict[str, str]] (optional) GCP resource labels that will be added to all resources you create
      with this profile. By default, we also add a few labels based on `wanna_project` section.
    - `bucket` - [str] (optional) GCS Bucket that can later be used in uploading manifests, storing logs, etc.
      depending on the resource type.
    - `service_account` - [str] (optional) GCP service account that will be used by the created resources.
    If not specified, usually the default service account for each resource type is used.
    - `network` - [str] Google Cloud VPC network name
    - `subnet` - [str] (optional) Google Cloud VPC subnetwork name
    - `kms_key` - [str] (optional) Customer managed enryption key given in format
      projects/{project_id}/locations/{region}/keyRings/{key_ring_id}/cryptoKeys/{key_id}
      If you get an error, please grant the Service Account with the Cloud KMS CryptoKey Encrypter/Decrypter role
    - `docker_repository` - [str] Wanna Docker Repository
    - `docker_registry` - [str] (optional) Wanna Docker Registry, usually in format {region}-docker.pkg.dev
    - `env_vars` - Dict[str, str] (optional) Environment variables to be propagated to all the notebooks and custom jobs
    """

    profile_name: str
    project_id: str
    zone: Optional[str]
    region: str
    labels: Optional[Dict[str, str]]
    bucket: str
    service_account: Optional[str]
    network: Optional[str]
    subnet: Optional[str]
    kms_key: Optional[str]
    docker_repository: str = "wanna"
    docker_registry: Optional[str]
    env_vars: Optional[Dict[str, str]]

    _ = validator("project_id", allow_reuse=True)(validators.validate_project_id)
    _ = validator("zone", allow_reuse=True)(validators.validate_zone)
    _ = validator("labels", allow_reuse=True)(validators.validate_labels)

    @root_validator(pre=True)
    def parse_region_from_zone(
        cls, values
    ):  # pylint: disable=no-self-argument,no-self-use
        """
        In some cases, the zone is defined and region not.
        Region can be easily parsed from zone.
        """
        zone, region = (
            values.get("zone"),
            values.get("region"),
        )
        if (region is None) and (zone is not None):
            values["region"] = get_region_from_zone(zone)
        return values

    _ = validator("region", allow_reuse=True)(validators.validate_region)
