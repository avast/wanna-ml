from typing import List, Optional

from pydantic import BaseModel, EmailStr, Extra


class WannaProjectModel(BaseModel, extra=Extra.forbid):
    """
    `wanna_project` section of the yaml config consists of the following inputs:

    - `name` - [str] the name of the wanna project should be unique, this name will be used in the docker service
      for naming docker images and in labeling GCP resources. Hence it can be used also for budget monitoring.
    - `version` - [str] Currently used only in labeling GCP resources, we expect to introduce new API versions
      and then this parameter will gain more importance.
    - `authors` - [List[str]] Email addresses, currently used only in GCP resource labeling but soon also in monitoring.
    - `billing_id` - [str] (optional) GCP Billing ID, needed for the budget report
    - `organization_id` - [str] (optional) GCP Organization ID, needed for the budget report
    """

    name: str
    version: str
    authors: List[EmailStr]
    billing_id: Optional[str]
    organization_id: Optional[str]
