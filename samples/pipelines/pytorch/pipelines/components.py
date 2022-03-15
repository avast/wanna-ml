import os
from typing import NamedTuple
import os
from datetime import datetime
import google_cloud_pipeline_components
import kfp
from google.cloud import aiplatform
from google.cloud.aiplatform import gapic as aip
from google.cloud.aiplatform import pipeline_jobs
from google.protobuf.json_format import MessageToDict
from google_cloud_pipeline_components import aiplatform as aip_components
from google_cloud_pipeline_components.experimental import custom_job
from kfp.v2 import compiler, dsl
from kfp.v2.dsl import Input, Metrics, Model, Output, component

@component(
    base_image="gcr.io/google.com/cloudsdktool/cloud-sdk:latest",
    packages_to_install=["google-cloud-build"],
    output_component_file="output_component/pipelines/build_custom_train_image.yaml",
)
def build_custom_train_image(
        project: str, gs_train_src_path: str, training_image_uri: str
) -> NamedTuple("Outputs", [("training_image_uri", str)]):
    """custom pipeline component to build custom training image using
    Cloud Build and the training application code and dependencies
    defined in the Dockerfile
    """

    import logging
    import os

    from google.cloud.devtools import cloudbuild_v1 as cloudbuild
    from google.protobuf.duration_pb2 import Duration

    # initialize client for cloud build
    logging.getLogger().setLevel(logging.INFO)
    build_client = cloudbuild.services.cloud_build.CloudBuildClient()

    # parse step inputs to get path to Dockerfile and training application code
    gs_dockerfile_path = os.path.join(gs_train_src_path, "Dockerfile")
    gs_train_src_path = os.path.join(gs_train_src_path, "trainer/")

    logging.info(f"training_image_uri: {training_image_uri}")

    # define build steps to pull the training code and Dockerfile
    # and build/push the custom training container image
    build = cloudbuild.Build()
    build.steps = [
        {
            "name": "gcr.io/cloud-builders/gsutil",
            "args": ["cp", "-r", gs_train_src_path, "."],
        },
        {
            "name": "gcr.io/cloud-builders/gsutil",
            "args": ["cp", gs_dockerfile_path, "Dockerfile"],
        },
        # enabling Kaniko cache in a Docker build that caches intermediate
        # layers and pushes image automatically to Container Registry
        # https://cloud.google.com/build/docs/kaniko-cache
        {
            "name": "gcr.io/kaniko-project/executor:latest",
            "args": [f"--destination={training_image_uri}", "--cache=true"],
        },
    ]
    # override default timeout of 10min
    timeout = Duration()
    timeout.seconds = 7200
    build.timeout = timeout

    # create build
    operation = build_client.create_build(project_id=project, build=build)
    logging.info("IN PROGRESS:")
    logging.info(operation.metadata)

    # get build status
    result = operation.result()
    logging.info("RESULT:", result.status)

    # return step outputs
    return (training_image_uri,)

@component(
    base_image="python:3.9",
    packages_to_install=["google-cloud-build"],
    output_component_file="output_component/pipelines/build_custom_serving_image.yaml",
)
def build_custom_serving_image(
        project: str, gs_serving_dependencies_path: str, serving_image_uri: str
) -> NamedTuple("Outputs", [("serving_image_uri", str)],):
    """custom pipeline component to build custom serving image using
    Cloud Build and dependencies defined in the Dockerfile
    """
    import logging
    import os

    from google.cloud.devtools import cloudbuild_v1 as cloudbuild
    from google.protobuf.duration_pb2 import Duration

    logging.getLogger().setLevel(logging.INFO)
    build_client = cloudbuild.services.cloud_build.CloudBuildClient()

    logging.info(f"gs_serving_dependencies_path: {gs_serving_dependencies_path}")
    gs_dockerfile_path = os.path.join(gs_serving_dependencies_path, "Dockerfile.serve")

    logging.info(f"serving_image_uri: {serving_image_uri}")
    build = cloudbuild.Build()
    build.steps = [
        {
            "name": "gcr.io/cloud-builders/gsutil",
            "args": ["cp", gs_dockerfile_path, "Dockerfile"],
        },
        # enabling Kaniko cache in a Docker build that caches intermediate
        # layers and pushes image automatically to Container Registry
        # https://cloud.google.com/build/docs/kaniko-cache
        {
            "name": "gcr.io/kaniko-project/executor:latest",
            "args": [f"--destination={serving_image_uri}", "--cache=true"],
        },
    ]
    # override default timeout of 10min
    timeout = Duration()
    timeout.seconds = 7200
    build.timeout = timeout

    # create build
    operation = build_client.create_build(project_id=project, build=build)
    logging.info("IN PROGRESS:")
    logging.info(operation.metadata)

    # get build status
    result = operation.result()
    logging.info("RESULT:", result.status)

    # return step outputs
    return (serving_image_uri,)

@component(
    base_image="python:3.9",
    packages_to_install=["google-cloud-aiplatform", "google-cloud-pipeline-components"],
    output_component_file="output_component/pipelines/make_prediction_request.yaml",
)
def make_prediction_request(project: str, bucket: str, endpoint: str, instances: list):
    """custom pipeline component to pass prediction requests to Vertex AI
    endpoint and get responses
    """
    import base64
    import logging

    from google.cloud import aiplatform
    from google.protobuf.json_format import Parse
    from google_cloud_pipeline_components.proto.gcp_resources_pb2 import \
        GcpResources

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
        if not isinstance(instance, (bytes, bytearray)):
            instance = instance.encode()
        logging.info(f"Input text: {instance.decode('utf-8')}")
        b64_encoded = base64.b64encode(instance)
        test_instance = [{"data": {"b64": f"{str(b64_encoded.decode('utf-8'))}"}}]
        response = _endpoint.predict(instances=test_instance)
        logging.info(f"Prediction response: {response.predictions}")

@component(
    base_image="python:3.9",
    packages_to_install=[
        "google-cloud-pipeline-components",
        "google-cloud-aiplatform",
        "pandas",
        "fsspec",
    ],
    output_component_file="output_component/pipelines/get_training_job_details.yaml",
)
def get_training_job_details(
        project: str,
        location: str,
        job_resource: str,
        eval_metric_key: str,
        model_display_name: str,
        metrics: Output[Metrics],
        model: Output[Model],
) -> NamedTuple(
    "Outputs", [("eval_metric", float), ("eval_loss", float), ("model_artifacts", str)]
):
    """custom pipeline component to get model artifacts and performance
    metrics from custom training job
    """
    import logging
    import shutil
    from collections import namedtuple

    import pandas as pd
    from google.cloud.aiplatform import gapic as aip
    from google.protobuf.json_format import Parse
    from google_cloud_pipeline_components.proto.gcp_resources_pb2 import \
        GcpResources

    # parse training job resource
    logging.info(f"Custom job resource = {job_resource}")
    training_gcp_resources = Parse(job_resource, GcpResources())
    custom_job_id = training_gcp_resources.resources[0].resource_uri
    custom_job_name = "/".join(custom_job_id.split("/")[-6:])
    logging.info(f"Custom job name parsed = {custom_job_name}")

    # get custom job information
    API_ENDPOINT = "{}-aiplatform.googleapis.com".format(location)
    client_options = {"api_endpoint": API_ENDPOINT}
    job_client = aip.JobServiceClient(client_options=client_options)
    job_resource = job_client.get_custom_job(name=custom_job_name)
    job_base_dir = job_resource.job_spec.base_output_directory.output_uri_prefix
    logging.info(f"Custom job base output directory = {job_base_dir}")

    # copy model artifacts
    logging.info(f"Copying model artifacts to {model.path}")
    destination = shutil.copytree(job_base_dir.replace("gs://", "/gcs/"), model.path)
    logging.info(destination)
    logging.info(f"Model artifacts located at {model.uri}/model/{model_display_name}")
    logging.info(f"Model artifacts located at model.uri = {model.uri}")

    # set model metadata
    start, end = job_resource.start_time, job_resource.end_time
    model.metadata["model_name"] = model_display_name
    model.metadata["framework"] = "pytorch"
    model.metadata["job_name"] = custom_job_name
    model.metadata["time_to_train_in_seconds"] = (end - start).total_seconds()

    # fetch metrics from the training job run
    metrics_uri = f"{model.path}/model/{model_display_name}/all_results.json"
    logging.info(f"Reading and logging metrics from {metrics_uri}")
    metrics_df = pd.read_json(metrics_uri, typ="series")
    for k, v in metrics_df.items():
        logging.info(f"     {k} -> {v}")
        metrics.log_metric(k, v)

    # capture eval metric and log to model metadata
    eval_metric = (
        metrics_df[eval_metric_key] if eval_metric_key in metrics_df.keys() else None
    )
    eval_loss = metrics_df["eval_loss"] if "eval_loss" in metrics_df.keys() else None
    logging.info(f"     {eval_metric_key} -> {eval_metric}")
    logging.info(f'     "eval_loss" -> {eval_loss}')

    model.metadata[eval_metric_key] = eval_metric
    model.metadata["eval_loss"] = eval_loss

    # return output parameters
    outputs = namedtuple("Outputs", ["eval_metric", "eval_loss", "model_artifacts"])

    return outputs(eval_metric, eval_loss, job_base_dir)

@component(
    base_image="python:3.9",
    packages_to_install=["torch-model-archiver"],
    output_component_file="output_component/pipelines/generate_mar_file.yaml",
)
def generate_mar_file(
        model_display_name: str,
        model_version: str,
        handler: str,
        model: Input[Model],
        model_mar: Output[Model],
) -> NamedTuple("Outputs", [("mar_env_var", list), ("mar_export_uri", str)]):
    """custom pipeline component to package model artifacts and custom
    handler to a model archive file using Torch Model Archiver tool
    """
    import logging
    import os
    import subprocess
    import time
    from collections import namedtuple
    from pathlib import Path

    logging.getLogger().setLevel(logging.INFO)

    # create directory to save model archive file
    model_output_root = model.path
    mar_output_root = model_mar.path
    export_path = f"{mar_output_root}/model-store"
    try:
        Path(export_path).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logging.warning(e)
        # retry after pause
        time.sleep(2)
        Path(export_path).mkdir(parents=True, exist_ok=True)

    # parse and configure paths for model archive config
    handler_path = (
        handler.replace("gs://", "/gcs/") + "predictor/custom_handler.py"
        if handler.startswith("gs://")
        else handler
    )
    model_artifacts_dir = f"{model_output_root}/model/{model_display_name}"
    extra_files = [
        os.path.join(model_artifacts_dir, f)
        for f in os.listdir(model_artifacts_dir)
        if f != "pytorch_model.bin"
    ]

    # define model archive config
    mar_config = {
        "MODEL_NAME": model_display_name,
        "HANDLER": handler_path,
        "SERIALIZED_FILE": f"{model_artifacts_dir}/pytorch_model.bin",
        "VERSION": model_version,
        "EXTRA_FILES": ",".join(extra_files),
        "EXPORT_PATH": f"{model_mar.path}/model-store",
    }

    # generate model archive command
    archiver_cmd = (
        "torch-model-archiver --force "
        f"--model-name {mar_config['MODEL_NAME']} "
        f"--serialized-file {mar_config['SERIALIZED_FILE']} "
        f"--handler {mar_config['HANDLER']} "
        f"--version {mar_config['VERSION']}"
    )
    if "EXPORT_PATH" in mar_config:
        archiver_cmd += f" --export-path {mar_config['EXPORT_PATH']}"
    if "EXTRA_FILES" in mar_config:
        archiver_cmd += f" --extra-files {mar_config['EXTRA_FILES']}"
    if "REQUIREMENTS_FILE" in mar_config:
        archiver_cmd += f" --requirements-file {mar_config['REQUIREMENTS_FILE']}"

    # run archiver command
    logging.warning("Running archiver command: %s", archiver_cmd)
    with subprocess.Popen(
            archiver_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ) as p:
        _, err = p.communicate()
        if err:
            raise ValueError(err)

    # set output variables
    mar_env_var = [{"name": "MODEL_NAME", "value": model_display_name}]
    mar_export_uri = f"{model_mar.uri}/model-store/"

    outputs = namedtuple("Outputs", ["mar_env_var", "mar_export_uri"])
    return outputs(mar_env_var, mar_export_uri)