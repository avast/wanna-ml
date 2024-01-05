import json
from datetime import datetime as dt

from google.cloud import aiplatform_v1, storage


def main(event, context):  # noqa: ARG001
    path = event["id"].rsplit("/", 1)[0].split("/", 1)[1]
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(event["bucket"])
    blob = bucket.blob(path)
    data = blob.download_as_text().splitlines()

    client = aiplatform_v1.PipelineServiceClient(
        client_options={"api_endpoint": "europe-west1-aiplatform.googleapis.com"},
    )

    for line in data:
        entry = json.loads(line)
        timestamp = entry["jsonPayload"]["startTime"]
        project_id = entry["logName"].split("/")[1]
        location = entry["resource"]["labels"]["location"]
        pipeline_id = entry["resource"]["labels"]["pipeline_job_id"]
        name = f"projects/{project_id}/locations/{location}/pipelineJobs/{pipeline_id}"
        delta = dt.now() - dt.strptime(
            timestamp[:-8].replace("T", " "), "%Y-%m-%d %H:%M:%S"
        )

        request = aiplatform_v1.GetPipelineJobRequest(name=name)
        pipeline = client.get_pipeline_job(request=request)
        if delta.total_seconds() > 3600 * float(
            pipeline.labels["wanna_sla_hours"].replace("_", ".")
        ):  # 60 seconds * 60 minutes
            request = aiplatform_v1.CancelPipelineJobRequest(name=name)
            client.cancel_pipeline_job(request=request)
