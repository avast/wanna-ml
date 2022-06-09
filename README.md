# WANNA-ML

WANNA-ML is a CLI tool that helps researchers, data scientists, and ML Engineers to easily
adapt to Google Cloud Platform (GCP) and get started on the cloud in almost no time.

It makes it easy to start a Jupyter notebook, run training jobs and pipelines or build Docker container 
and export logs to Tensorboards.

We build on top of Vertex-AI managed services and integrate with other GCP services like Cloud Build and Artifact Registry
to provide you with a standardized structure for managing ML assets on GCP.

[Check out the full online documentation]() and follow to tutorial for concepts and example introduction.

## Installation for users

[Please refer to this section of the documentation]().


## WANNA ML Pipelines

WANNA provides a veneer over [Vertex AI Pipelines(Kubeflow)](https://cloud.google.com/vertex-ai/docs/pipelines/introduction) that simplify a series of common and repetitive tasks, whilst automating scheduling, compilation and deployment.

Compilation values are passed through to the Kubeflow pipelines via ENV vars at compilation time.

### Usage

```bash
# Parses wanna, builds containers, compiles kubeflow pipeline
wanna pipeline build --file samples/pipelines/sklearn/wanna.yaml --name wanna-sklearn-sample

# Parses wanna, builds & push containers, compiles and packages kubeflow pipeline, 
# prepares wanna-manifest.json to deploy and run pipelines
wanna pipeline push --file samples/pipelines/sklearn/wanna.yaml --name wanna-sklearn-sample --version 0.0.1

# deploys cloud scheduler and cloud function to run pipeline from wanna-manifest.json
wanna pipeline deploy --file samples/pipelines/sklearn/wanna.yaml --name wanna-sklearn-sample --env local --version 0.0.1

# runs Vertex AI Pipeline based on a wanna-manifest.json
wanna pipeline run --maniest gs://path/version/x.z/wanna-manifest.json --params path/to/params.yaml

# runs Vertex AI Pipeline based on wanna.yaml
wanna pipeline run --file samples/pipelines/sklearn/wanna.yaml --sync --params samples/pipelines/sklearn/params.yaml
```

## WANNA Notebooks
One of the goals of wanna is to allow Avast ML team to get started quickly with Vertex AI platform 
and have freedom to explore within a sa  

Builds containers and creates user-managed vertex-ai notebooks where Notebooks:
* can have an owner for single person use
* can have a service account for team use
* can have custom containers with any required dependencies
* can have a default containers with just requirement.txt
* can have any machine spec including any number of GPUs
* notebooks will have WANNA default gcp labels for cost tracking

It also allows for deletion of notebooks with user confirmation

### Expected GCP roles
* Artifact Registry Writer
* Cloud Functions Invoker
* Cloud Scheduler Job Runner
* Notebooks Admin
* Storage Object Creator
* Vertex AI User
* Viewer

### Usage

```bash
wanna notebook create --file samples/notebook/julia/wanna.yaml -n wanna-notebook-julia

wanna notebook create --file samples/pipelines/sklearn/wanna.yaml -n wanna-sklearn-sample-notebook

wanna notebook delete --file samples/pipelines/sklearn/wanna.yaml -n wanna-sklearn-sample-notebook
```

## WANNA Managed notebooks
Managed notebooks allow Avast ML team to get started quickly with Vertex AI platform 
without setting up the VM details. You can change the underlying hardware later on.

Creates managed vertex-ai notebooks where Notebooks:
* must have an owner for single person use
* can have different kernels
* can have any machine spec including any number of GPUs
* will have WANNA default gcp labels for cost tracking
* can connect to Dataproc Clusters and Metastores
* will have all the buckets from a given project mounted

It also allows for deletion and sync (with wanna.yaml) of notebooks with the user confirmation

### Expected GCP roles
* Artifact Registry Writer
* Cloud Functions Invoker
* Cloud Scheduler Job Runner
* Notebooks Admin
* Storage Object Creator
* Vertex AI User
* Viewer

### Usage

```bash
wanna managed-notebook create --file samples/notebook/managed-notebook/wanna.yaml

wanna managed-notebook delete --file samples/notebook/managed-notebook/wanna.yaml -n joao-notebook

wanna managed-notebook sync --file samples/notebook/managed-notebook/wanna.yaml
```

## WANNA Jobs
Custom Jobs are split into two categories depending on it intended use

### Custom Jobs
* [ ] TODO

### Training Jobs
* [ ] TODO

### Usage

```bash
wanna job build --file samples/custom_job/wanna.yaml -n custom-training-job-with-python-package

wanna job build --file samples/custom_job/wanna.yaml -n custom-training-job-with-containers

wanna job build --file samples/custom_job/wanna.yaml -n custom-job-with-containers
````

## Development

### Environment setup

To hack on WANNA you will need `docker` daemon, a `Python >=3.8` environment setup and [gcloud cli](https://cloud.google.com/sdk/docs/install-sdk) installed

```bash

# Login to GCP
gcloud auth login

# Auth against GCP docker registries
gcloud auth configure-docker europe-west1-docker.pkg.dev 
gcloud auth configure-docker europe-west3-docker.pkg.dev
 

# create a wanna work environment
conda create -n wanna python=3.8 poetry nomkl 

# Install project dependencies (including dev dependencies) and load our cli  into a Python virtual environment managed by Poetry 
poetry install

# Run the cli during dev
wanna version

# Check all is good in paradise - pylint, isort, mypy, tests
task build

```

### Editable mode
Project based on the `setuptools` package had to be installed in "editable mode"
so that changes are picked up between tests. This in turn could cause other
issues sometimes.

`poetry` handles the editable mode for you, no special commands are necessary.

### Generating documentation
If you have changed the sphinx documentation or docstrings of plugins, you must
generate the HTML documentation from source. You can use the `task` plugin:
```bash
task docs-serve
```

Alternatively if you want to see docs in localhost before pushing
```bash
task docs-deploy
```

## Reading
* https://python-poetry.org/
* https://pre-commit.com/
