import config as cfg
from components.data.get_data import get_data_op
from components.predictor import make_prediction_request
from components.trainer.eval_model import eval_model_op
from components.trainer.train_xgb_model import train_xgb_model_op
from google_cloud_pipeline_components import aiplatform as aip_components
from kfp.v2 import dsl
from kfp.v2.dsl import component


@component(
    base_image="python:3.9",
    packages_to_install=["slack-webhook-cli"],
)
def slack_notification(slack_channel: str, status: str):
    import logging
    import subprocess

    logging.getLogger().setLevel(logging.INFO)

    webhook = "https://hooks.slack.com/services/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"

    icon = "https://a.slack-edge.com/production-standard-emoji-assets/13.0/apple-medium/274c.png"

    args = ["slack", "-w", webhook, "-c", slack_channel, f":white_check_mark: {status}"]
    result = subprocess.run(args, capture_output=True)

    if result.returncode > 0:
        logging.error(result.stderr.decode())
        exit(result.returncode)
    else:
        logging.info(result.stdout.decode())


@dsl.pipeline(
    # A name for the pipeline. Use to determine the pipeline Context.
    name=cfg.PIPELINE_NAME,
)
def wanna_sklearn_sample(eval_acc_threshold: float):

    # ===================================================================
    # Get pipeline result notification
    # ===================================================================
    # collect datasets provided by sklearn
    exit_task = (
        slack_notification(
            slack_channel="#p-mlops-alerts",
            status="Kubeflow pipeline: {{workflow.name}} has {{workflow.status}}!",
        )
        .set_display_name("Slack Notification")
        .set_caching_options(False)
    )

    with dsl.ExitHandler(exit_task):

        # ===================================================================
        # collect datasets
        # ===================================================================
        # collect datasets provided by sklearn
        dataset_op = get_data_op()

        # ===================================================================
        # train model
        # ===================================================================
        # simple model training directly in component
        train_op = train_xgb_model_op(dataset_op.outputs["dataset_train"])

        # ===================================================================
        # eval model
        # ===================================================================
        # collect model metrics for deployment condition
        eval_op = eval_model_op(
            test_set=dataset_op.outputs["dataset_test"], xgb_model=train_op.outputs["model_artifact"]
        )

        # ========================================================================
        # model deployment when threshold condition is met
        # ========================================================================
        with dsl.Condition(
            eval_op.outputs["test_score"] > eval_acc_threshold,
            name="model-deploy-decision",
        ):
            # ===================================================================
            # create model resource
            # ===================================================================
            # upload model to vertex ai
            model_upload_task = (
                aip_components.ModelUploadOp(
                    project=cfg.PROJECT_ID,
                    display_name=cfg.MODEL_DISPLAY_NAME,
                    location=cfg.REGION,
                    serving_container_image_uri=cfg.SERVE_IMAGE_URI,
                    labels=cfg.PIPELINE_LABELS,
                    artifact_uri=train_op.outputs["model_artifact_path"],
                )
                .set_display_name("Upload model")
                .after(eval_op)
            )

            # ===================================================================
            # create Vertex AI Endpoint
            # ===================================================================
            # create endpoint to deploy one or more models
            # An endpoint provides a service URL where the prediction requests are sent
            endpoint_create_task = (
                aip_components.EndpointCreateOp(
                    project=cfg.PROJECT_ID,
                    location=cfg.REGION,
                    display_name=cfg.MODEL_NAME + "-model-endpoint",
                    labels=cfg.PIPELINE_LABELS,
                )
                .set_display_name("Create model endpoint")
                .after(model_upload_task)
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
                [
                    36,
                    14.25,
                    21.72,
                    93.63,
                    633.0,
                    0.09823,
                    0.1098,
                    0.1319,
                    0.05598,
                    0.1885,
                    0.06125,
                    0.286,
                    1.019,
                    2.657,
                    24.91,
                    0.005878,
                    0.02995,
                    0.04815,
                    0.01161,
                    0.02028,
                    0.004022,
                    15.89,
                    30.36,
                    116.2,
                    799.6,
                    0.1446,
                    0.4238,
                    0.5186,
                    0.1447,
                    0.3591,
                    0.1014,
                ],
                [
                    226,
                    10.44,
                    15.46,
                    66.62,
                    329.6,
                    0.1053,
                    0.07722,
                    0.006643,
                    0.01216,
                    0.1788,
                    0.0645,
                    0.1913,
                    0.9027,
                    1.208,
                    11.86,
                    0.006513,
                    0.008061,
                    0.002817,
                    0.004972,
                    0.01502,
                    0.002821,
                    11.52,
                    19.8,
                    73.47,
                    395.4,
                    0.1341,
                    0.1153,
                    0.02639,
                    0.04464,
                    0.2615,
                    0.08269,
                ],
            ]
            response = make_prediction_request.make_prediction_request(
                project=cfg.PROJECT_ID,
                bucket=cfg.BUCKET,
                endpoint=model_deploy_task.outputs["gcp_resources"],
                instances=test_instances,
            ).set_display_name("Make prediction request")
            response
