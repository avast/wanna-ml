---
title: WANNA Tutorial
summary: Introduction to WANNA tutorial and how to follow it
authors:
    - Joao Da Silva
    - Michal Mrázek
date: 2022-04-06
---

# WANNA - Get started

### Use Docker Image
For your convenience, we have prepared a Docker image with everything you need to get started (gcloud, wanna-ml and docker client).
```bash
docker pull michalmrazek9/wanna-ml

docker run -it michalmrazek9/wanna-ml

$ wanna version
```

If you also want to build and push docker images from inside of our docker image, use this volume:
```bash
docker run -it -v /var/run/docker.sock:/var/run/docker.sock michalmrazek9/wanna-ml
```

### Installation
Install using `pip install -U wanna-ml`.

For more information on the installation process and requirements, visit out [installation page in documentation](https://avast.github.io/wanna-ml/installation)

### Authentication
WANNA-ML relies on `gcloud` for user authentication. 

1. Install the `gcloud` CLI - follow [official guide](https://cloud.google.com/sdk/docs/install)
2. Authenticate with the `gcloud init`
3. Set you Google Application Credentials `gcloud auth application-default login`

### Docker Build
You can use a local Docker daemon to build Docker images, but it is not required. 
You are free to choose between local building on GCP Cloud Build. 
If you prefer local Docker image building, install  [Docker Desktop](https://www.docker.com/products/docker-desktop/).

### GCP IAM Roles and Permissions
Different WANNA-ML calls require different GCP permissions to create given resources on GCP. Our [documentation page](https://avast.github.io/wanna-ml/)
lists recommended GCP IAM roles for each `wanna` command.