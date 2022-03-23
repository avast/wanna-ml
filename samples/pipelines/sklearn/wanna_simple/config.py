import json
import os
from datetime import datetime

# Env exported from wanna pipeline cli command
PIPELINE_NAME_PREFIX = "WANNA_SKLEARN_SAMPLE"  # snake_cased pipeline name in wanna config

PROJECT_ID = os.getenv(f"{PIPELINE_NAME_PREFIX}_PROJECT_ID")
BUCKET = os.getenv(f"{PIPELINE_NAME_PREFIX}_BUCKET")
REGION = os.getenv(f"{PIPELINE_NAME_PREFIX}_REGION")
PIPELINE_NAME = os.getenv(f"{PIPELINE_NAME_PREFIX}_PIPELINE_NAME")
PIPELINE_JOB_ID = os.getenv(f"{PIPELINE_NAME_PREFIX}_PIPELINE_JOB_ID")
VERSION = os.getenv(f"{PIPELINE_NAME_PREFIX}_PIPELINE_VERSION", datetime.now().strftime("%Y%m%d%H%M%S"))
PIPELINE_LABELS = json.loads(os.getenv(f"{PIPELINE_NAME_PREFIX}_PIPELINE_LABELS", "{}"))

# Pipeline config
MODEL_NAME = f"{PIPELINE_NAME.lower()}"  # type: ignore
PIPELINE_ROOT = f"{BUCKET}/pipeline_root/{MODEL_NAME}"
MODEL_DISPLAY_NAME = f"{MODEL_NAME}-{VERSION}"

# Custom GPU training config
TRAIN_IMAGE_URI = os.environ.get(
    f"{PIPELINE_NAME_PREFIX}_TRAIN_DOCKER_URI", "europe-docker.pkg.dev/vertex-ai/prediction/xgboost-cpu.1-4:latest"
)  # Fail
# MACHINE_TYPE = "n1-standard-8"
# REPLICA_COUNT = "1"
# ACCELERATOR_TYPE = "NVIDIA_TESLA_T4"
# ACCELERATOR_COUNT = "1"
# NUM_WORKERS = 1

# Custom Serving Config
SERVE_IMAGE_URI = os.environ.get(
    f"{PIPELINE_NAME_PREFIX}_SERVE_DOCKER_URI", "europe-docker.pkg.dev/vertex-ai/prediction/xgboost-cpu.1-4:latest"
)  # Fail
SERVING_HEALTH_ROUTE = "/ping"
SERVING_PREDICT_ROUTE = "/predict"
SERVING_CONTAINER_PORT = [{"containerPort": 7080}]
SERVING_MACHINE_TYPE = "n1-standard-4"
SERVING_MIN_REPLICA_COUNT = 1
SERVING_MAX_REPLICA_COUNT = 2
SERVING_TRAFFIC_SPLIT = '{"0": 100}'
