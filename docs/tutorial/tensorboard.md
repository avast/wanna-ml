---
title: WANNA Tensorboard
summary: How to use wanna tensorboard command
authors:
    - Joao Da Silva
date: 2022-04-06
---

# WANNA Tensorboard
Many GCP services can work directly with tensorboards. For thar reason we offer you
a simple solution how to include them in your resources.

Tensorboards can either be used as a separate resource with `wanna tensorboard create/list/delete`
or you can use them similarly to docker images as a dependency of other resources with `tensorboard_ref` key. In the second case,
tensorboards are automatically created when needed and used when already existing.

### Tensorboard parameters
Tensorboards take only two paremeters:

- `name` - name of the tensorboard, not to confuse with resource name (name=`my-tensorboard`,
  resource name=`projects/{project}/locations/{location}/tensorboards/{tensorboard_id}/`)
- `region` - GCP location

### Example
```
tensorboards:
  - name: wanna-sample-dashboard

jobs:
  - name: custom-training-job-with-python-package
    region: europe-west1
    worker:
      python_package:
        docker_image_ref: tensorflow
        package_gcs_uri: "gs://wanna-ml/trainer-0.1.tar.gz"
        module_name: "trainer.task"
      args: ['--epochs=100', '--steps=100', '--distribute=single']
      gpu:
          accelerator_type: NVIDIA_TESLA_V100
          count: 1
    tensorboard_ref: my-nice-tensorboard
```

#### Integration with other services
Integration with tensorboard depends on the resource, but for example Custom Jobs
pass the path to the tensorboard in env var `AIP_TENSORBOARD_LOG_DIR`.
When using keras for training, the integration in your code could look like this:

```python
from tensorflow.keras.callbacks import TensorBoard

# Define Tensorboard as a Keras callback
tensorboard = TensorBoard(
 log_dir=os.getenv("AIP_TENSORBOARD_LOG_DIR"),
 histogram_freq=1,
 write_images=True
)
keras_callbacks = [tensorboard]

model.fit(x=train_dataset, epochs=args.epochs, steps_per_epoch=args.steps, callbacks=keras_callbacks)
```
Check the job samples for complete example.

With notebooks, you will need `tb-gcp-uploader` as specified [here](https://cloud.google.com/vertex-ai/docs/experiments/tensorboard-overview).
We also export the link to the tensorboard directory as `AIP_TENSORBOARD_LOG_DIR`. But you will
need to handle the log export yourself. 

### Roles and permissions
Permission and suggested roles (applying the principle of least privilege) required for tensorboard manipulation:

| WANNA action  | Permissions | Suggested Roles  |
| -----------   | ----------- | ------ |
| create  | `aiplatform.tensorboards.create` ,`aiplatform.tensorboards.list`       | `roles/aiplatform.user`     |
| delete  | `aiplatform.tensorboards.delete` ,`aiplatform.tensorboards.list`        | `roles/aiplatform.user`       |
| list    | `aiplatform.tensorboards.list`, `aiplatform.tensorboardExperiments.*`, `aiplatform.tensorboardRuns.*`        | `roles/aiplatform.viewer` , `roles/aiplatform.user`      |
| access the dashboard    | `aiplatform.tensorboards.recordAccess` | `roles/aiplatform.tensorboardWebAppUser`  |

[Full list of available roles and permission.](https://cloud.google.com/vertex-ai/docs/general/access-control)