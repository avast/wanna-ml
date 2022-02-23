from pydantic import BaseModel, Extra, validator, root_validator, EmailStr
from typing import Optional


from wanna.cli.utils.gcp import validators
from wanna.cli.utils.gcp.gcp import get_region_from_zone


class GCPSettingsModel(BaseModel, extra=Extra.forbid):
    project_id: str
    zone: Optional[str]
    region: Optional[str]
    labels: Optional[str]
    service_account: Optional[str]

    _ = validator("project_id", allow_reuse=True)(validators.validate_project_id)
    _ = validator("zone", allow_reuse=True)(validators.validate_zone)

    @root_validator(pre=True)
    def parse_region_from_zone(cls, values):
        """
        In some cases, the zone is defined and region not.
        Region can be easily parsed from zone.
        """
        zone, region, project_id = (
            values.get("zone"),
            values.get("region"),
            values.get("project_id"),
        )
        if (region is None) and (zone is not None):
            values["region"] = get_region_from_zone(project_id, zone)
        return values

    _ = validator("region", allow_reuse=True)(validators.validate_region)
