---
title: WANNA notebook
summary: How to use wanna notebook command
authors:
  - Joao Da Silva
  - Michal Mrázek
date: 2022-04-06
---
  
# WANNA Notebook
We offer a simple way of managing Jupyter Notebooks on GCP using 
[Vertex AI Workbench Instances](https://cloud.google.com/vertex-ai/docs/workbench/instances/introduction), 
with multiple ways to set your environment, mount a GCS bucket, and more.

::: wanna.core.models.workbench.InstanceModel
    :docstring:

### Notebook Environments
There are two distinct possibilities for your environment.

- Use a custom docker image, we recommend you build on top of GCP notebook ready images, either with
using one of their images as a base or by using the `notebook_ready_image` docker type. 
  It is also possible to build your image from scratch, but please follow GCP's recommended 
  principles and port settings as described [here](https://cloud.google.com/vertex-ai/docs/workbench/user-managed/custom-container).
```
docker:
  images:
    - build_type: local_build_image
      name: custom-notebook-container
      context_dir: .
      dockerfile: Dockerfile.notebook
  repository: wanna-samples
  cloud_build: true

notebooks:
  - name: wanna-notebook-custom-container
    environment:
      docker_image_ref: custom-notebook-container
```  
- Use a virtual machine image with preconfigured python libraries containing TensorFlow, PyTorch, R and more.
Currently, GCP does not offer any customization, so you just pass empty dict to the `vm_image`.

```
notebooks:
  - name: wanna-notebook-vm
    machine_type: n1-standard-4
    environment:
     vm_image: {}
```    

### Mounting buckets
We can automatically mount GCS buckets with `gcsfuse` during the notebook startup.

Example:
``` 
    bucket_mounts:
      - bucket_name: us-burger-gcp-poc-mooncloud
        bucket_dir: data
        local_path: /home/jupyter/mounted/gcs
``` 

### Tensorboard integration
`tb-gcp-uploader` is needed to upload the logs to the tensorboard instance. A detailed
tutorial on this tool can be found [here](https://cloud.google.com/vertex-ai/docs/experiments/tensorboard-overview).

If you set the `tensorboard_ref` in the WANNA yaml config, we will export the tensorboard resource name
as `AIP_TENSORBOARD_LOG_DIR`.

### Roles and permissions
Permission and suggested roles (applying the principle of least privilege) required for notebook manipulation:

| WANNA action  | Permissions | Suggested Roles  |
| -----------   | ----------- | ------ |
| create  | See [full list](https://cloud.google.com/vertex-ai/docs/workbench/user-managed/iam)      | `roles/notebooks.runner`, `roles/notebooks.admin`     |
| delete  | see [full list](https://cloud.google.com/vertex-ai/docs/workbench/user-managed/iam)       | `roles/notebooks.admin`       |

For accessing the JupyterLab web interface, you must grant the user access to the service account used by the notebooks instance. 
If the instance owner is set, only this user can access the web interface.

[Full list of available roles and permission.](https://cloud.google.com/vertex-ai/docs/workbench/user-managed/iam)

### Local development and SSH
If you wish to develop code in your local IDE and run it on Vertex-AI notebooks, we have a solution for you.
Assuming your notebook is already running, you can set up an SSH connection via:

```
wanna notebook ssh --background -n notebook_name
```

Wanna will create an SSH tunnel using GCP IAP from your local environment to your notebook.

The `--background/-b` flag means that the tunnel will be created in the background and you can 
access the notebook running in GCP at `localhost:8080` (port can be customized with `--port`).
The second possibility is to use `--interactive/-i` and that will start a bash inside the Compute Engine
instance backing your Vertex-AI notebook.

Once you set an `--background` connection to the notebook, you can use your favorite IDE to develop
in the notebook. Here we share instructions on how to use VSCode for this.

#### Connecting with VSCode
1. Install Jupyter Extension 
2. Create a new file with the type Jupyter notebook
3. Select the Jupyter Server: local button in the global Status bar or run the 
   Jupyter: Specify local or remote Jupyter server for connections command from the Command Palette (⇧⌘P).
   
4. Select option `Existing URL` and input `http://localhost:8080`
5. You should be connected. If you get an error saying something like `'_xsrf' argument missing from POST.`,
it is because the VSCode cannot start a python kernel in GCP. The current workaround is to manually start
   a kernel at `http://localhost:8080` and then in the VSCode connect to the exiting kernel in the right upper corner.
   

A more detailed guide on setting a connection with VSCode to Jupyter can be found at https://code.visualstudio.com/docs/datascience/jupyter-notebooks.


### Example
```
notebooks:
  - name: wanna-notebook-trial
    service_account:
    owner: 
    machine_type: n1-standard-4
    labels:
      notebook_usecase: wanna-notebook-sample-simple-pip
    environment:
      vm_image: {}
    gpu:
      count: 1
      accelerator_type: NVIDIA_TESLA_V100
      install_gpu_driver: true
    boot_disk:
      disk_type: pd_standard
      size_gb: 100
    data_disk:
      disk_type: pd_standard
      size_gb: 100
    bucket_mounts:
      - bucket_name: us-burger-gcp-poc-mooncloud
        bucket_dir: data
        local_path: /home/jupyter/mounted/gcs
    tensorboard_ref: my-super-tensorboard
```
