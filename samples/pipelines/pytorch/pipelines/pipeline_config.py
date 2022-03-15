import os
from datetime import datetime

PROJECT_ID = os.getenv("PROJECT_ID", "")
BUCKET = os.getenv("BUCKET_NAME", "")

REGION = os.getenv("REGION", "europe-west-4")

APP_NAME = os.getenv("APP_NAME", "finetuned-bert-classifier")
VERSION = datetime.now().strftime("%Y%m%d%H%M%S")
MODEL_NAME = APP_NAME
MODEL_DISPLAY_NAME = f"{MODEL_NAME}-{VERSION}"

PIPELINE_NAME = f"pytorch-{APP_NAME}"
PIPELINE_ROOT = f"{BUCKET}/pipeline_root/{MODEL_NAME}"
GCS_STAGING = f"{BUCKET}/pipeline_root/{MODEL_NAME}"

TRAIN_IMAGE_URI = f"gcr.io/{PROJECT_ID}/pytorch_gpu_train_{MODEL_NAME}"
SERVE_IMAGE_URI = f"gcr.io/{PROJECT_ID}/pytorch_cpu_predict_{MODEL_NAME}"

MACHINE_TYPE = "n1-standard-8"
REPLICA_COUNT = "1"
ACCELERATOR_TYPE = "NVIDIA_TESLA_T4"
ACCELERATOR_COUNT = "1"
NUM_WORKERS = 1

SERVING_HEALTH_ROUTE = "/ping"
SERVING_PREDICT_ROUTE = f"/predictions/{MODEL_NAME}"
SERVING_CONTAINER_PORT= [{"containerPort": 7080}]
SERVING_MACHINE_TYPE = "n1-standard-4"
SERVING_MIN_REPLICA_COUNT = 1
SERVING_MAX_REPLICA_COUNT=1
SERVING_TRAFFIC_SPLIT='{"0": 100}'