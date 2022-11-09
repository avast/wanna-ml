import json
import os
from datetime import datetime

from caseconverter import snakecase

# Env exported from wanna pipeline cli command
PIPELINE_NAME_PREFIX = snakecase("{{ cookiecutter.project_slug }}-pipeline").upper()

PROJECT_ID = os.getenv(f"{PIPELINE_NAME_PREFIX}_PROJECT_ID")
BUCKET = os.getenv(f"{PIPELINE_NAME_PREFIX}_BUCKET")
REGION = os.getenv(f"{PIPELINE_NAME_PREFIX}_REGION")
PIPELINE_NAME = os.getenv(f"{PIPELINE_NAME_PREFIX}_PIPELINE_NAME")
PIPELINE_JOB_ID = os.getenv(f"{PIPELINE_NAME_PREFIX}_PIPELINE_JOB_ID")
VERSION = os.getenv(f"{PIPELINE_NAME_PREFIX}_VERSION", datetime.now().strftime("%Y%m%d%H%M%S"))
PIPELINE_LABELS = json.loads(os.getenv(f"{PIPELINE_NAME_PREFIX}_PIPELINE_LABELS", "{}"))
TENSORBOARD = os.getenv(f"{PIPELINE_NAME_PREFIX}_TENSORBOARD")

# Pipeline config
MODEL_NAME = f"{PIPELINE_NAME.lower()}"  # type: ignore
PIPELINE_ROOT = f"{BUCKET}/pipeline-root/{MODEL_NAME}"
MODEL_DISPLAY_NAME = f"{MODEL_NAME}-{VERSION}"
