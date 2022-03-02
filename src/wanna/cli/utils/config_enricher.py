from typing import Dict
from wanna.cli.models.wanna_project import WannaProjectModel
from wanna.cli.models.gcp_settings import GCPSettingsModel


def add_labels(instance_dict: Dict, new_labels: Dict[str, str]) -> Dict:
    """
    Add new labels to the instance model.
    Args:
        instance_dict: dictionary representing one instance
        new_labels: new labels to be added

    Returns:
        instance_dict: dictionary representing one instance with added labels
    """
    labels = instance_dict.get("labels") or {}
    labels.update(new_labels)
    instance_dict["labels"] = labels
    return instance_dict


def generate_default_labels(wanna_project: WannaProjectModel) -> Dict[str, str]:
    """
    Get the default labels (GCP labels) that will be used with all instances based on wanna_project info.
    Args:
        wanna_project

    Returns:
        default labels
    """
    return {
        "wanna_project": wanna_project.name,
        "wanna_project_version": str(wanna_project.version).replace(".", "__"),
        "wanna_project_author": wanna_project.author.partition("@")[0].replace(
            ".", "_"
        ),
    }


def enrich_instance_info_with_gcp_settings_dict(
    instance_dict: dict, gcp_settings: GCPSettingsModel
) -> dict:
    """
    The dictionary instance_dict is updated with values from gcp_settings. This allows you to set values such as
    project_id and zone only on the wanna-ml config level but also give you the freedom to set separately for each
    notebook, jobs, etc. The values as at the instance level take precedence over general wanna-ml settings.

    Args:
        instance_dict: dict with values from wanna-ml config from one instance (one job, one notebook)
        gcp_settings: GCPSettings model

    Returns:
        dict: enriched with general gcp_settings if those information was not set on instance level

    """
    gcp_settings_dict = gcp_settings.dict().copy()
    gcp_settings_dict = {k: v for k, v in gcp_settings_dict.items() if v is not None}
    instance_info = gcp_settings_dict
    instance_info.update(instance_dict)
    return instance_info


def enrich_instance_with_gcp_settings(cls, values_inst, values):
    """
    Enrich dictionary representing one instance (one notebook, job, etc.)
    with information wanna_project and gcp_settings. This is useful in scenario when
    some parameters (project_id) are needed for all instances, but you can set it
    only on general gcp_settings level.

    Args:
        cls: pydantic class
        values_inst: values representing one instance
        values: values for the whole pydantic object

    Returns:
        values_inst: values representing one instance enriched with information from wanna_project and gcp_settings
    """
    values_inst = enrich_instance_info_with_gcp_settings_dict(
        instance_dict=values_inst, gcp_settings=values.get("gcp_settings")
    )
    labels = generate_default_labels(wanna_project=values.get("wanna_project"))
    values_inst = add_labels(instance_dict=values_inst, new_labels=labels)
    return values_inst
