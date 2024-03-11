# WANNA-ML

---

<p align="center" font-style="italic"> 
<em> Complete MLOps framework for Vertex-AI  </em>
</p>

---

<p align="center">
<a href="https://github.com/avast/wanna-ml/actions/workflows/build.yml" target="_blank">
    <img src="https://github.com/avast/wanna-ml/actions/workflows/build.yml/badge.svg" alt="Build">
</a>
<a href="https://github.com/avast/wanna-ml/actions/workflows/release.yml" target="_blank">
    <img src="https://github.com/avast/wanna-ml/actions/workflows/release.yml/badge.svg" alt="Release">
</a>
<a href="https://codecov.io/gh/avast/wanna-ml" target="_blank">
    <img src="https://codecov.io/gh/avast/wanna-ml/branch/master/graph/badge.svg?token=TAFWK4GJPR" alt="Coverage">
</a>
<a href="https://pypi.org/project/wanna-ml/" target="_blank">
    <img src="https://img.shields.io/pypi/v/wanna-ml?color=%2334D058&label=pypi%20package" alt="Package version">
</a>
</p>

# About WANNA-ML

WANNA-ML is a CLI tool that helps researchers, data scientists, and ML Engineers quickly adapt to Google Cloud Platform (GCP) and get started on the cloud in almost no time.

It makes it easy to start a Jupyter notebook, run training jobs and pipelines, build a Docker container, export logs to Tensorboards, and much more.

We build on top of Vertex-AI managed services and integrate with other GCP services like Cloud Build and Artifact Registry to provide you with a standardized structure for managing ML assets on GCP.


## Help

See the [documentation](https://avast.github.io/wanna-ml/) for more details.


## Get started

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

## Examples
Jump to [the samples](https://github.com/avast/wanna-ml/tree/master/samples) to see a complete solution 
for various use cases.

## Issues
Please report issues to [GitHub](https://github.com/avast/wanna-ml/issues).

## Contributing
Your contributions are always welcome, see [CONTRIBUTING.md](https://github.com/avast/wanna-ml/blob/master/CONTRIBUTING.md) for more information.
If you like WANNA-ML, don't forget to give our project a star! 

## Licence
Distributed under the MIT License - see [LICENSE](https://github.com/avast/wanna-ml/blob/master/LICENCE).
