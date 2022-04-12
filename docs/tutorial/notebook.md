---
title: WANNA notebook
summary: How to use wanna notebook command
authors:
  - Joao Da Silva
date: 2022-04-06
---
  
# WANNA Notebook
We offer a simple way of managing Jupyter Notebooks on GCP, with multiple way
to set your environment, mount GCS bucket and more.

### Notebook Environments
There are two distinct possibilities for your environment.

- Use a custom docker image, we recommend you build on top of GCP notebook ready images, either with
using one of their image as a base or by using `notebook_ready_image` docker type. 
  It is also possible to build your image from scratch, but please follow GCP recommended 
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
- Use a virtual machine image with preconfigured python libraries or tensorflow / pytorch / R and more.
Complete list of available images can be found [here](https://cloud.google.com/vertex-ai/docs/workbench/user-managed/images).

```
notebooks:
  - name: wanna-notebook-vm
    machine_type: n1-standard-4
    environment:
     vm_image:
       framework: pytorch
       version: 1-9-xla
       os: debian-10
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
`tb-gcp-uploader` is needed to upload the logs to tensorboard instance. Detailed
tutorial to this tool can be found [here](https://cloud.google.com/vertex-ai/docs/experiments/tensorboard-overview).

If you set the `tensorboard_ref` in WANNA yaml config, we will export the tensorboard resource name
as `AIP_TENSORBOARD_LOG_DIR`.

### Additional notebook parameters
Apart from setting your computing environment, tensorboard and bucket mounts, we offer additional parameters for you:

- `zone` - GCP location zone
- `machine_type` - GCP Compute Engine machine type 
- `tags` - GCP Compute Engine tags to add to runtime
- `metadata`- Custom metadata to apply to this instance
- `service_account` - The email address of a service account to use when running the execution
- `instance_owner` - Currently supports one owner only. If not specified, all of the service account users of your VM instance’s service account can use the instance.
  If specified, only the owner will be able to access to notebook.
- `gpu`- The hardware GPU accelerator used on this instance. 
- `boot_disk` - Boot disk configuration to attach to this instance.
- `data_disk` - Data disk configuration to attach to this instance.
- `network` - The name of the VPC that this instance is in.

### Example
```
notebooks:
  - name: wanna-notebook-trial
    service_account:
    instance_owner: 
    machine_type: n1-standard-4
    labels:
      notebook_usecase: wanna-notebook-sample-simple-pip
    environment:
      vm_image:
        framework: pytorch
        version: 1-9-xla
        os: debian-10
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
