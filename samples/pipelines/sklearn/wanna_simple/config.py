import json
import os
from datetime import datetime

# Env exported from wanna pipeline cli command
PIPELINE_NAME_PREFIX = "WANNA_SKLEARN_SAMPLE"  # snake_cased pipeline name in wanna config

PROJECT_ID = os.getenv(f"{PIPELINE_NAME_PREFIX}_PROJECT_ID")
BUCKET = os.getenv(f"{PIPELINE_NAME_PREFIX}_BUCKET")
REGION = os.getenv(f"{PIPELINE_NAME_PREFIX}_REGION")
PIPELINE_NAME = os.getenv(f"{PIPELINE_NAME_PREFIX}_PIPELINE_NAME")
PIPELINE_EXPERIMENT = os.environ[f"{PIPELINE_NAME_PREFIX}_PIPELINE_EXPERIMENT"]
VERSION = os.getenv(f"{PIPELINE_NAME_PREFIX}_PIPELINE_VERSION", datetime.now().strftime("%Y%m%d%H%M%S"))
PIPELINE_LABELS = json.loads(os.getenv(f"{PIPELINE_NAME_PREFIX}_PIPELINE_LABELS", "{}"))
TENSORBOARD = os.getenv(f"{PIPELINE_NAME_PREFIX}_TENSORBOARD")

# Pipeline config
MODEL_NAME = f"{PIPELINE_NAME.lower()}"  # type: ignore
PIPELINE_ROOT = f"{BUCKET}/pipeline_root/{MODEL_NAME}"
MODEL_DISPLAY_NAME = f"{MODEL_NAME}-{VERSION}"

# custom training image
TRAIN_IMAGE_URI = os.environ[f"TRAIN_DOCKER_URI"]  # Fail

# Custom Serving Config
# "europe-docker.pkg.dev/vertex-ai/prediction/xgboost-cpu.1-4:latest"
SERVE_IMAGE_URI = os.environ[f"SERVE_DOCKER_URI"]  # Yes, fail during compilation

SERVING_MACHINE_TYPE = "n1-standard-4"
SERVING_MIN_REPLICA_COUNT = 1
SERVING_MAX_REPLICA_COUNT = 2
SERVING_TRAFFIC_SPLIT = '{"0": 100}'
