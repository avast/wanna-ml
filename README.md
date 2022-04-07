# WANNA ML

[![TeamCity](https://teamcity.ida.avast.com/app/rest/builds/buildType:BigDataSystem_Projects_Wanna_ML_Publish___Release,branch:<default>/statusIcon)](https://teamcity.ida.avast.com/project/BigDataSystem_Projects_Wanna_ML?mode=builds)
[![Artifactory](https://pypi-badger.luft.avast.com/image/pypi-local/wanna-ml)](https://artifactory.ida.avast.com/artifactory/webapp/#/artifacts/browse/tree/General/pypi-local/wanna-ml)

WANNA manage ML on Vertex AI :-)

[Check out the full online documentation](https://git.int.avast.com/pages/bds/wanna-ml/) and follow to tutorial for concepts and example introduction.

Slack channel: [#t-mlops-developers](https://avast.slack.com/messages/t-mlops-developers/)

CML page for the project is [here](https://cml.avast.com/display/BDS/Cloud+ML+-+WANNA).

## Installation for users

[Please refer to this section of the documentation](https://git.int.avast.com/pages/bds/wanna-ml/installation/).


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
On of the goals of wanna is to allow Avast ML team to get started quickly with Vertex AI platform 
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

## WANNA Jobs
Custom Jobs are split into two categories depending on it intended use

### Custom Jobs
* [ ] TODO

### Training Jobs
* [ ] TODO

### Usage

```bash
wanna job create --file samples/custom_job/wanna.yaml -n custom-training-job-with-python-package

wanna job create --file samples/custom_job/wanna.yaml -n custom-training-job-with-containers

wanna job create --file samples/custom_job/wanna.yaml -n custom-job-with-containers
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
poetry run wanna

# Run tests with pytest
poetry run pytest

# Install precommit hooks for code quality checks
poetry run pre-commit install

# Check all is good in paradise - pylint, isort, mypy, 
poetry run task build

# Activate poetry venv for commiting work
poetry shell

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
	$ poetry run task docs-serve
```

Alternatively if you want to see docs in localhost before pushing
```bash
	$ poetry run task docs-deploy
```

## Reading
* https://python-poetry.org/
* https://pre-commit.com/
