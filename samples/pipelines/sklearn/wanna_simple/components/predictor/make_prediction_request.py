from kfp.dsl import component


@component(
    base_image="python:3.9",
    packages_to_install=["google-cloud-aiplatform", "google-cloud-pipeline-components"],
)
def make_prediction_request(
    project: str, bucket: str, endpoint: str, instances: list[list[float]]
):
    """custom pipeline component to pass prediction requests to Vertex AI
    endpoint and get responses
    """
    import logging

    from google.cloud import aiplatform
    from google.protobuf.json_format import Parse
    from google_cloud_pipeline_components.proto.gcp_resources_pb2 import GcpResources

    logging.getLogger().setLevel(logging.INFO)
    aiplatform.init(project=project, staging_bucket=bucket)

    # parse endpoint resource
    logging.info(f"Endpoint = {endpoint}")
    gcp_resources = Parse(endpoint, GcpResources())
    endpoint_uri = gcp_resources.resources[0].resource_uri
    endpoint_id = "/".join(endpoint_uri.split("/")[-8:-2])
    logging.info(f"Endpoint ID = {endpoint_id}")

    # define endpoint client
    _endpoint = aiplatform.Endpoint(endpoint_id)

    # call prediction endpoint for each instance
    for instance in instances:
        response = _endpoint.predict(instances=[instance])
        logging.info(f"Prediction response: {response.predictions}")
