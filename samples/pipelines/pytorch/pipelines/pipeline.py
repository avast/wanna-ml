from typing import List
import os
from typing import NamedTuple

import google_cloud_pipeline_components
from google.cloud import aiplatform
from google.cloud.aiplatform import gapic as aip
from google.cloud.aiplatform import pipeline_jobs
from google.protobuf.json_format import MessageToDict
from google_cloud_pipeline_components import aiplatform as aip_components
from google_cloud_pipeline_components.experimental import custom_job
from kfp.v2 import compiler, dsl
from kfp.v2.dsl import Input, Metrics, Model, Output, component
import pipeline_config as cfg
from datetime import datetime
from .components import *

PROJECT_ID = cfg.PROJECT_ID
APP_NAME = cfg.APP_NAME
BUCKET_NAME = cfg.BUCKET
REGION = cfg.REGION
PIPELINE_ROOT = cfg.PIPELINE_ROOT


def get_timestamp():
    return datetime.now().strftime("%Y%m%d%H%M%S")


TIMESTAMP = get_timestamp()
print(f"TIMESTAMP = {TIMESTAMP}")


@dsl.pipeline(
    name=cfg.PIPELINE_NAME,
    pipeline_root=cfg.PIPELINE_ROOT,
)
def pytorch_text_classifier_pipeline(
        pipeline_job_id: str,
        gs_train_script_path: str,
        gs_serving_dependencies_path: str,
        eval_acc_threshold: float,
        is_hp_tuning_enabled: str = "n",
        training_args: List[str] = ["--num-epochs", "2", "--model-name", cfg.MODEL_NAME]
):
    # ========================================================================
    # build custom training container image
    # ========================================================================
    # build custom container for training job passing the
    # GCS location of the training application code
    build_custom_train_image_task = (
        build_custom_train_image(
            project=cfg.PROJECT_ID,
            gs_train_src_path=gs_train_script_path,
            training_image_uri=cfg.TRAIN_IMAGE_URI,
        ).set_caching_options(True)
            .set_display_name("Build custom training image")
    )

    # ========================================================================
    # model training
    # ========================================================================
    # train the model on Vertex AI by submitting a CustomJob
    # using the custom container (no hyper-parameter tuning)
    # define training code arguments
    # training_args = ["--num-epochs", "2", "--model-name", cfg.MODEL_NAME]
    # define job name
    JOB_NAME = f"{cfg.MODEL_NAME}-train-pytorch-cstm-cntr-{TIMESTAMP}"
    GCS_BASE_OUTPUT_DIR = f"{cfg.GCS_STAGING}/{TIMESTAMP}"
    # define worker pool specs
    worker_pool_specs = [
        {
            "machine_spec": {
                "machine_type": cfg.MACHINE_TYPE,
                "accelerator_type": cfg.ACCELERATOR_TYPE,
                "accelerator_count": cfg.ACCELERATOR_COUNT,
            },
            "replica_count": cfg.REPLICA_COUNT,
            "container_spec": {"image_uri": cfg.TRAIN_IMAGE_URI, "args": training_args},
        }
    ]

    run_train_task = (
        custom_job.CustomTrainingJobOp(
            project=cfg.PROJECT_ID,
            location=cfg.REGION,
            display_name=JOB_NAME,
            base_output_directory=GCS_BASE_OUTPUT_DIR,
            worker_pool_specs=worker_pool_specs,
        ).set_display_name("Run custom training job")
         .after(build_custom_train_image_task)
    )

    # ========================================================================
    # get training job details
    # ========================================================================
    training_job_details_task = get_training_job_details(
        project=cfg.PROJECT_ID,
        location=cfg.REGION,
        job_resource=run_train_task.output,
        eval_metric_key="eval_accuracy",
        model_display_name=cfg.MODEL_NAME,
    ).set_display_name("Get custom training job details")

    # ========================================================================
    # model deployment when condition is met
    # ========================================================================
    with dsl.Condition(
            training_job_details_task.outputs["eval_metric"] > eval_acc_threshold,
            name="model-deploy-decision",
    ):
        # ===================================================================
        # create model archive file
        # ===================================================================
        create_mar_task = generate_mar_file(
            model_display_name=cfg.MODEL_NAME,
            model_version=cfg.VERSION,
            handler=gs_serving_dependencies_path,
            model=training_job_details_task.outputs["model"],
        ).set_display_name("Create MAR file")

        # ===================================================================
        # build custom serving container running TorchServe
        # ===================================================================
        # build custom container for serving predictions using
        # the trained model artifacts served by TorchServe
        build_custom_serving_image_task = build_custom_serving_image(
            project=cfg.PROJECT_ID,
            gs_serving_dependencies_path=gs_serving_dependencies_path,
            serving_image_uri=cfg.SERVE_IMAGE_URI,
        ).set_display_name("Build custom serving image")

        # ===================================================================
        # create model resource
        # ===================================================================
        # upload model to vertex ai
        model_upload_task = (
            aip_components.ModelUploadOp(
                project=cfg.PROJECT_ID,
                display_name=cfg.MODEL_DISPLAY_NAME,
                serving_container_image_uri=cfg.SERVE_IMAGE_URI,
                serving_container_predict_route=cfg.SERVING_PREDICT_ROUTE,
                serving_container_health_route=cfg.SERVING_HEALTH_ROUTE,
                serving_container_ports=cfg.SERVING_CONTAINER_PORT,
                serving_container_environment_variables=create_mar_task.outputs[
                    "mar_env_var"
                ],
                artifact_uri=create_mar_task.outputs["mar_export_uri"],
            )
                .set_display_name("Upload model")
                .after(build_custom_serving_image_task)
        )

        # ===================================================================
        # create Vertex AI Endpoint
        # ===================================================================
        # create endpoint to deploy one or more models
        # An endpoint provides a service URL where the prediction requests are sent
        endpoint_create_task = (
            aip_components.EndpointCreateOp(
                project=cfg.PROJECT_ID,
                display_name=cfg.MODEL_NAME + "-endpoint",
            )
                .set_display_name("Create endpoint")
                .after(create_mar_task)
        )

        # ===================================================================
        # deploy model to Vertex AI Endpoint
        # ===================================================================
        # deploy models to endpoint to associates physical resources with the model
        # so it can serve online predictions
        model_deploy_task = aip_components.ModelDeployOp(
            endpoint=endpoint_create_task.outputs["endpoint"],
            model=model_upload_task.outputs["model"],
            deployed_model_display_name=cfg.MODEL_NAME,
            dedicated_resources_machine_type=cfg.SERVING_MACHINE_TYPE,
            dedicated_resources_min_replica_count=cfg.SERVING_MIN_REPLICA_COUNT,
            dedicated_resources_max_replica_count=cfg.SERVING_MAX_REPLICA_COUNT,
            traffic_split=cfg.SERVING_TRAFFIC_SPLIT,
        ).set_display_name("Deploy model to endpoint")

        # ===================================================================
        # test model deployment
        # ===================================================================
        # test model deployment by making online prediction requests
        test_instances = [
            "Jaw dropping visual affects and action! One of the best I have seen to date.",
            "Take away the CGI and the A-list cast and you end up with film with less punch.",
        ]
        predict_test_instances_task = make_prediction_request(
            project=cfg.PROJECT_ID,
            bucket=cfg.BUCKET,
            endpoint=model_deploy_task.outputs["gcp_resources"],
            instances=test_instances,
        ).set_display_name("Test model deployment making online predictions")
        predict_test_instances_task


if __name__ == "__main__":
    import pathlib

    PIPELINE_JSON_SPEC_PATH = str((pathlib.Path(__file__).parent / "pytorch_text_classifier_pipeline_spec.json").resolve())

    # PIPELINE_JSON_SPEC_PATH = "./pipelines/pytorch_text_classifier_pipeline_spec.json"
    compiler.Compiler().compile(
        pipeline_func=pytorch_text_classifier_pipeline, package_path=PIPELINE_JSON_SPEC_PATH
    )

    aiplatform.init(project=cfg.PROJECT_ID, location=cfg.REGION)

    # define pipeline parameters
    # NOTE: These parameters can be included in the pipeline config file as needed

    PIPELINE_JOB_ID = f"pipeline-{APP_NAME}-{get_timestamp()}"
    TRAIN_APP_CODE_PATH = f"{BUCKET_NAME}/{APP_NAME}/train/"
    SERVE_DEPENDENCIES_PATH = f"{BUCKET_NAME}/{APP_NAME}/serve/"

    pipeline_params = {
        "pipeline_job_id": PIPELINE_JOB_ID,
        "gs_train_script_path": TRAIN_APP_CODE_PATH,
        "gs_serving_dependencies_path": SERVE_DEPENDENCIES_PATH,
        "eval_acc_threshold": 0.87,
        "is_hp_tuning_enabled": "n",
    }

    # define pipeline job
    pipeline_job = pipeline_jobs.PipelineJob(
        display_name=cfg.PIPELINE_NAME,
        job_id=PIPELINE_JOB_ID,
        template_path=PIPELINE_JSON_SPEC_PATH,
        pipeline_root=PIPELINE_ROOT,
        parameter_values=pipeline_params,
        enable_caching=False,
    )

    # submit pipeline job for execution
    response = pipeline_job.run(sync=True)
    response

    # underscores are not supported in the pipeline name, so
    # replace underscores with hyphen
    df_pipeline = aiplatform.get_pipeline_df(pipeline=cfg.PIPELINE_NAME.replace("_", "-"))
    df_pipeline
