# Generated file do not change
import json

from google.cloud import aiplatform

PROJECT_ID = "{{manifest.project}}"
REGION = "{{manifest.location}}"
PIPELINE_ROOT = "{{manifest.pipeline_root}}"
PIPELINE_LABELS = json.loads("""{{labels}}""")


def process_request(request):
    # TODO: from wanna.sdk.pipeline import runner
    # runner.run(path_to_manifest)
    # runner.run(version, env)

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
    parameter_values = request_json["parameter_values"]

    aiplatform.init(
        project=PROJECT_ID,
        location=REGION,
    )

    job = aiplatform.PipelineJob(
        display_name="{{manifest.pipeline_name}}",
        # job_id=pipeline_job_id, #TODO: add me
        template_path=pipeline_spec_uri,
        pipeline_root=PIPELINE_ROOT,
        enable_caching=True,
        parameter_values=parameter_values,
        labels=PIPELINE_LABELS,
    )

    job.submit()
    return "Job submitted"
