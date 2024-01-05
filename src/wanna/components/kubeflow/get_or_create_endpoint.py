from typing import Dict, Optional

from kfp.v2 import dsl


@dsl.component(
    base_image="python:3.9",
    packages_to_install=[
        "google-cloud-pipeline-components==2.5.0",
        "google-cloud-aiplatform==1.35.0",
    ],
)
def get_or_create_endpoint(
    project: str,
    location: str,
    display_name: str,
    endpoint: dsl.Output[dsl.Artifact],
    labels: Dict[str, str] = {},
    network: Optional[str] = None,
):
    import logging

    from google.api_core.client_options import ClientOptions
    from google.cloud import aiplatform_v1

    api_endpoint = f"{location}-aiplatform.googleapis.com"
    vertex_uri_prefix = f"https://{api_endpoint}/v1/"

    client = aiplatform_v1.EndpointServiceClient(
        client_options=ClientOptions(
            api_endpoint=api_endpoint,
        )
    )

    list_request = aiplatform_v1.ListEndpointsRequest(
        parent=f"projects/{project}/locations/{location}",
    )
    resp = client.list_endpoints(request=list_request)
    # Match endpoints on display name and also if they are public / private
    endpoints = [
        e
        for e in resp
        if e.display_name == display_name and e.network == (network or "")
    ]

    if len(endpoints) > 0:
        logging.info("Already existing endpoints found")
        # If multiple endpoints are matched, take the newest one by update time
        sorted_endpoints = sorted(
            endpoints, key=lambda ep: ep.update_time, reverse=True
        )

        endpoint_resource_name = sorted_endpoints[0].name

    else:
        logging.info("No existing endpoint found, we will create one")
        endpoint_model = aiplatform_v1.Endpoint()
        endpoint_model.display_name = display_name
        endpoint_model.labels = labels
        if network:
            endpoint_model.network = network
        request = aiplatform_v1.CreateEndpointRequest(
            parent=f"projects/{project}/locations/{location}",
            endpoint=endpoint_model,
        )
        operation = client.create_endpoint(request=request)
        response = operation.result()

        endpoint_resource_name = response.name

    endpoint.uri = vertex_uri_prefix + endpoint_resource_name
    endpoint.metadata = {"resourceName": endpoint_resource_name}
