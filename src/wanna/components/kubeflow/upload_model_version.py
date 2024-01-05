from typing import Dict, List, Optional

from google_cloud_pipeline_components.types.artifact_types import VertexModel
from kfp import dsl


@dsl.component(
    base_image="python:3.9",
    packages_to_install=[
        "google-cloud-pipeline-components==2.3.0",
        "google-cloud-aiplatform==1.31.0",
    ],
)
def upload_model_version(
    project: str,
    location: str,
    display_name: str,
    serving_container_image_uri: str,
    artifact_uri: str,
    model: dsl.Output[VertexModel],
    model_output_path: dsl.OutputPath(str),  # type: ignore
    labels: Dict[str, str] = {},
    version_aliases: List[str] = [],
    metadata: List[str] = [],
    model_description: Optional[str] = None,
    version_description: Optional[str] = None,
):
    """
    Creates a new model in Vertex-AI Model Registry. If multiple models with same display_name
    already exist, it will take the one with latest update_time and create only new version.
    """
    import json
    import logging

    from google.api_core.client_options import ClientOptions
    from google.cloud import aiplatform_v1

    api_endpoint = f"{location}-aiplatform.googleapis.com"
    vertex_uri_prefix = f"https://{api_endpoint}/v1/"

    client = aiplatform_v1.ModelServiceClient(
        client_options=ClientOptions(
            api_endpoint=api_endpoint,
        )
    )

    parent = f"projects/{project}/locations/{location}"
    list_request = aiplatform_v1.ListModelsRequest(
        parent=parent, filter=f'displayName="{display_name}"'
    )
    resp = client.list_models(request=list_request)
    models = resp.models

    if len(models) > 0:
        logging.info(
            "Already existing model with same display name found, will create a new version"
        )
        # If multiple models are matched, take the newest one by update time
        sorted_models = sorted(
            models, key=lambda model: model.update_time, reverse=True
        )
        parent_model_resource_name = sorted_models[0].name

    else:
        logging.info("No existing model with this display name found")
        parent_model_resource_name = None

    vertex_model = aiplatform_v1.Model()
    vertex_model.display_name = display_name
    vertex_model.container_spec = aiplatform_v1.types.ModelContainerSpec()
    vertex_model.container_spec.image_uri = serving_container_image_uri
    vertex_model.artifact_uri = artifact_uri
    if version_aliases:
        vertex_model.version_aliases = version_aliases
    if model_description:
        vertex_model.description = model_description
    if version_description:
        vertex_model.version_description = version_description
    vertex_model.labels = labels
    vertex_model.metadata = metadata

    request = aiplatform_v1.UploadModelRequest(
        parent_model=parent_model_resource_name,
        parent=parent,
        model=vertex_model,
    )
    operation = client.upload_model(request=request)
    response = operation.result()
    new_model_resource_name = response.model

    model.uri = vertex_uri_prefix + new_model_resource_name
    model.metadata = {"resourceName": new_model_resource_name}

    with open(model_output_path, "w") as output_file:
        output_file.write(json.dumps(model.__dict__))
