# Generated file do not change
import json
import os
from typing import Any, Dict

import pendulum
from google.cloud import aiplatform
from jinja2 import Environment

PROJECT_ID = os.getenv("PROJECT_ID")
REGION = os.getenv("REGION")
PIPELINE_ROOT = os.getenv("PIPELINE_ROOT")
PIPELINE_NETWORK = os.getenv("PIPELINE_NETWORK")
PIPELINE_SERVICE_ACCOUNT = os.getenv("PIPELINE_SERVICE_ACCOUNT")
PIPELINE_EXPERIMENT = os.getenv("PIPELINE_EXPERIMENT")
PIPELINE_LABELS = json.loads(
    os.environ["PIPELINE_LABELS"]
)  # if not define we won't run it
PIPELINE_JOB_ID = os.getenv("PIPELINE_JOB_ID")
ENCRYPTION_SPEC_KEY_NAME = os.getenv("ENCRYPTION_SPEC_KEY_NAME")

_jinja_env = Environment()
_jinja_env.globals.update(modules={"pendulum": pendulum})


def _update_time_template(params: Dict[str, Any]):
    for k, v in params.items():
        if isinstance(v, str):
            v = _jinja_env.from_string(v).render()
        params[k] = v

    return params


def process_request(request):
    """Processes the incoming HTTP request.

    Args:
      request (flask.Request): HTTP request object.

    Returns:
      The response text or any set of values that can be turned into a Response
      object using `make_response
      <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """

    # decode http request payload and translate into JSON object
    request_str = request.data.decode("utf-8")
    request_json = json.loads(request_str)

    pipeline_spec_uri = request_json["pipeline_spec_uri"]
    parameter_values = _update_time_template(request_json["parameter_values"])
    enable_caching = request_json.get("enable_caching", False)

    aiplatform.init(project=PROJECT_ID, location=REGION, experiment=PIPELINE_EXPERIMENT)

    job = aiplatform.PipelineJob(
        display_name="{{manifest.pipeline_name}}",
        job_id=PIPELINE_JOB_ID,
        template_path=pipeline_spec_uri,
        pipeline_root=PIPELINE_ROOT,
        enable_caching=enable_caching,
        parameter_values=parameter_values,
        labels=PIPELINE_LABELS,
        encryption_spec_key_name=ENCRYPTION_SPEC_KEY_NAME,
    )

    job.submit(
        service_account=PIPELINE_SERVICE_ACCOUNT,
        network=PIPELINE_NETWORK,
        experiment=PIPELINE_EXPERIMENT,
    )

    return "Job submitted"
