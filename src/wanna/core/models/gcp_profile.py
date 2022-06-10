from typing import Dict, Optional

from pydantic import BaseModel, Extra, root_validator, validator

from wanna.core.utils import validators
from wanna.core.utils.gcp import get_region_from_zone


class GCPProfileModel(BaseModel, extra=Extra.forbid):
    profile_name: str
    project_id: str
    zone: Optional[str]
    region: str
    labels: Optional[Dict[str, str]]
    bucket: str
    service_account: Optional[str]
    network: str

    _ = validator("project_id", allow_reuse=True)(validators.validate_project_id)
    _ = validator("zone", allow_reuse=True)(validators.validate_zone)

    @root_validator(pre=True)
    def parse_region_from_zone(cls, values):  # pylint: disable=no-self-argument,no-self-use
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
