# !pip install google-cloud-notebooks

from google.cloud.notebooks_v1.services.notebook_service import (
    NotebookServiceAsyncClient,
)
from google.cloud.notebooks_v1.types import Instance, CreateInstanceRequest, VmImage

notebook_client = NotebookServiceAsyncClient()

project_id = "us-burger-gcp-poc"
location = "europe-west4-a"

instances = notebook_client.list_instances(
    parent=f"projects/{project_id}/locations/{location}"
)

type(instances)

try:
    inst = await instances
except Exception as e:
    error = e
    print(e)

inst

instance = Instance(
    vm_image=VmImage(
        project=f"deeplearning-platform-release", image_family="common-cpu-notebooks"
    ),
    machine_type="n1-standard-4",
)

instance_request = CreateInstanceRequest(
    parent=f"projects/{project_id}/locations/{location}",
    instance_id="my-new-notebook",
    instance=instance,
)
instance_request

resp = notebook_client.create_instance(instance_request)

try:
    inst = await resp
except Exception as e:
    error = e
    print(e)

resp

print(inst)

await inst.done()

inst.metadata

inst.operation.error
