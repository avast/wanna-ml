#!/bin/bash

set -e


# Current script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

export BUCKET_NAME="gs://wanna-sample-pytorch" # <-- CHANGE TO YOUR BUCKET NAME
export APP_NAME="finetuned-bert-classifier"
export PROJECT_ID="us-burger-gcp-poc"

# REGION: select a region from https://cloud.google.com/vertex-ai/docs/general/locations#available_regions
# or use the default '`europe-west4`'. The region is where the job will be run.
export REGION="europe-west4"

# validate bucket name
if [ "${BUCKET_NAME}" = "[your-bucket-name]" ]
then
  echo "[ERROR] INVALID VALUE: Please update the variable BUCKET_NAME with valid Cloud Storage bucket name. Exiting the script..."
  exit 1
fi

gsutil cp "${SCRIPT_DIR}/Dockerfile" "${BUCKET_NAME}/${APP_NAME}/train/"

gsutil cp -r "${SCRIPT_DIR}/trainer/" "${BUCKET_NAME}/${APP_NAME}/train/"

gsutil ls -Rl "${BUCKET_NAME}/${APP_NAME}/train/"

gsutil cp "${SCRIPT_DIR}/predictor/Dockerfile.serve" "${SCRIPT_DIR}/predictor/custom_handler.py" "${SCRIPT_DIR}/predictor/index_to_name.json" "${BUCKET_NAME}/${APP_NAME}/serve/predictor/"

gsutil ls -lR "${BUCKET_NAME}/${APP_NAME}/serve/"

export PYTHONPATH="${SCRIPT_DIR}/pipelines:${PYTHONPATH}"

python "${SCRIPT_DIR}/pipelines/pipeline.py"

