---
title: WANNA Pipelines
summary: How to use wanna to build and deploy ML pipelines into Vertex AI
authors:
    - Joao Da Silva
    - Michal Mrázek
date: 2022-04-06
---

# WANNA ML Pipelines

WANNA ML Pipelines aim at reducing the friction on development cycle to release whilst providing project organization for independent and testable components. It wrapps Kubeflow V2 pipelines with a build and deployment tools for managed GCP VertexAI ML Pipelines service. It has several utils and conventions to reduce boilerplate and speed up development.

## Tutorial Get started

In this tutorial we will go over several steps that will bootstrap and run a Vertex AI Pipeline(Kubeflow V2) through wanna cli.

### Setup environment
```bash

# Login to GCP
gcloud auth login

# Auth against GCP docker registries
gcloud auth configure-docker europe-west1-docker.pkg.dev 

# Create python env
conda create -n pipeline-tutorial python=3.8 poetry

conda activate pipeline-tutorial

pip install wanna-ml

```

### Initialize WANNA project

```bash
wanna init --template blank
```

For this turorial we will be using Avast cloud-lab-304213 GCP project as it is available to everyone.

Answer the following questions:

```bash
project_name [project_name]: pipeline_tutorial
project_owner_fullname [project owner]:  
project_owner_email [you@avast.com]: 
project_version [0.0.0]: 
project_description [Link to WANNA project page on CML]: 
project_slug [project_name]: 
gcp_project_id []: cloud-lab-304213
gcp_service_account []: jacekhebdatest@cloud-lab-304213.iam.gserviceaccount.com
gcp_bucket []: wanna-ml-west1-jh
```

Complete installation process

```bash
cd pipeline_tutorial

poetry install
```

Build blank pipeline to check all is well in paradise

```bash
wanna pipeline build
```

## Components
Now that we have a blank bootstraped Kubeflow V2 pipeline we need to add components. In this tutorial we choose to go with self contained components that are independent and testable. There is a recomended structure but it can be tedious to repeat every time and this is where `wanna` comes in to aliviate this boilerplate.

### Create first component for data prep
The first component we will create is a data component where we can do some data preparation for the rest of the pipeline

```bash 
wanna components create --output-dir pipeline/components/
```

the output should be something like

```bash

component_name [component_name]: data
component_author [component author]: Joao Da Silva
component_author_email [you@gendigital.com]: joao.silva1@gendigital.com
component_version [0.0.0]: 
component_description [Describe your component]: data component for WANNA pipeline tutorial        
component_url [Link to MLOps project page]: 
component_slug [data]: 
component_docker_ref [data]: 
Select component_framework:
1 - base-cpu
2 - base-cu110
3 - base-cu113
4 - pytorch-xla-1.11
5 - pytorch-gpu-1.10
6 - pytorch-gpu-1.11
7 - sklearn-0.24
8 - tf-cpu.2-6
9 - tf-cpu.2-8
10 - tf-gpu-slim.2-6
11 - tf-gpu-slim.2-8
12 - xgboost-cpu.1-1
Choose from 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 [1]: 1
```

as a result you can see the following tree structure, which for the most part is a common python `lib` structure whith the exception of kubeflow's component.yaml
```bash
tree pipeline/components/data

pipeline/components/data
├── Dockerfile
├── README.md
├── component.yaml
├── setup.py
├── src
│   └── data
│       ├── __init__.py
│       └── data.py
└── tests
    └── test_data.py

4 directories, 9 files
```

You may also notice that a Dockerfile is present and here is where the python data `lib` is installed and executed. However we do need to add this Dockerfile to `wanna.yaml` so that wanna knows about it and can build it and export it.

Update wanna `docker.images` yaml array with

```bash
images
    - build_type: local_build_image
      name: data
      context_dir: pipeline/components/data/
      dockerfile: pipeline/components/data/Dockerfile
``` 

and add the docker ref `data` into the pipeline in wanna.yaml so that wanna can link these and expose the docker tag and pipeline compine time. Update wanna.yamll path `pipelines[0].docker_image_ref` with `docker_image_ref: [data]`.

It should now look like:

```bash
pipelines:
  - name: pipeline-tutorial-pipeline
    schedule:
      cron: 2 * * * *
    bucket: gs://wanna-tensorflow-sample-dev
    pipeline_function: project_name.pipeline.wanna_pipeline
    pipeline_params: pipeline/params.yaml
    docker_image_ref: ["data"]
    tensorboard_ref: pipeline-tutorial-board
```

Earlier I mentioned `expose the docker tag`, this means wanna exports every docker tag from `docker.images` array as `${NAME_DOCKER_URI}` so in this component you can see in the yaml `${DATA_DOCKER_URI}` which gets replaced at compile time, this way we have the possibility to have dynamic Kubeflow components versioned according to current pipeline release.

Next we may wat to make this component part of our `poetry` build so that we can run tests, linter and whatnot from a single place.

Lets edit our `pyproject.toml` as follows:
```toml
[tool.poetry.dependencies]
python = ">=3.8,<3.11"
data = {path = "pipeline/components/data", develop=true}
```

> from `poetry >= 1.2` we  will be able to just run `poetry add pipeline/components/data --editable`.

Let's install our data lib into the environment and run some
```bash
poetry lock && poetry install
```
At this point running `python -m data.data --help` should show:

```
Usage: python -m data.data [OPTIONS]

Options:
  --project TEXT
  --location TEXT
  --experiment-name TEXT
  --help                  Show this message and exit.
```

as well as a quick test `pytest -s pipeline/components/data` or go full scale with pre-commit hook `git init . && git add . && task build`. This will fail on `flake8` as expected, as we will be using the var which flake8 complains about.

You can now see that you have a self contained component and testable, ready to be added to the kubeflow pipeline.

## Pipeline

::: wanna.core.models.pipeline.PipelineModel
    :docstring:

WANNA template creates two files that allow to put together the Kubeflow V2 pipeline that will then be deployed to GCP Vertex AI Pipelines.

`pipeline/config.py` captures wanna compile time exposed environment variables and provides this as configuration to `pipeline/pipeline.py`.

With that in mind let's add our data component to `pipeline.py`.

First we imoprt wanna component loader that will replace ENV vars, namely the container

```python

from wanna.components.loader import load_wanna_component

```

Secondly we will load the actual component. `wanna_pipeline` function should now look like this:

```python
@dsl.pipeline(
    # A name for the pipeline. Use to determine the pipeline Context.
    name=cfg.PIPELINE_NAME,
    pipeline_root=cfg.PIPELINE_ROOT
)
def wanna_pipeline(eval_acc_threshold: float):
    pipeline_dir = Path(__file__).parent.resolve()

    # ===================================================================
    # Get pipeline result notification
    # ===================================================================
    exit_task = (
        on_exit()
        .set_display_name("On Exit Dummy Task")
        .set_caching_options(False)
    )

    with dsl.ExitHandler(exit_task):
        load_wanna_component(f"{pipeline_dir}/components/data/component.yaml")(
            experiment_name=cfg.MODEL_DISPLAY_NAME
        ).set_display_name("Data prep")

```

now with everything in place, lets build the pipeline with `wanna pipeline build` or with `wanna pipeline build --quick` if you want to skip docker builds and just verify Kubeflow compiles and components have correct inputs and outputs connected.


### Running the pipeline in `dev` mode

When WANNA runs a pipeline from local it will,

1. build & push the component containers to Google Docker registry
2. compile the kubeflow pipeline and upload to gcs the resulting pipeline json spec
3. compile and upload to gcs wanna manifest that allows to run the pipeline from anywhere
4. Trigger the pipeline run and print its dashboard url and running state

Assuming we are on `✔ Compiling pipeline pipeline-tutorial-pipeline` succeeded we can now actually run the pipeline.

```bash
wanna pipeline run --name pipeline-tutorial-pipeline --params pipeline/params.yaml --version dev --sync
```

if all goes with the plan you should see something along the lines(we will be improving the stdout logging overtime):

```
 Reading and validating wanna yaml config
ℹ GCP profile 'default' will be used.
✔ Skipping build for context_dir=pipeline/components/data, dockerfile=pipeline/components/data/Dockerfile and image europe-west1-docker.pkg.dev/cloud-lab-304213/wanna-samples/pipeline_tutorial/data:dev
⠸ Compiling pipeline pipeline-tutorial-pipeline
✔ Compiling pipeline pipeline-tutorial-pipeline
✔ Pushing docker image europe-west1-docker.pkg.dev/cloud-lab-304213/wanna-samples/pipeline_tutorial/data:dev
ℹ Uploading wanna running manifest to gs://wanna-ml-west1-jh/pipeline-root/pipeline-tutorial-pipeline/deployment/release/dev/wanna_manifest.json
ℹ Uploading vertex ai pipeline spec to gs://wanna-ml-west1-jh/pipeline-root/pipeline-tutorial-pipeline/deployment/release/dev/pipeline_spec.json
✔ Pushing pipeline pipeline-tutorial-pipeline
⠦ Running pipeline pipeline-tutorial-pipeline in sync modeCreating PipelineJob
⠋ Running pipeline pipeline-tutorial-pipeline in sync modePipelineJob created. Resource name: projects/968728188698/locations/europe-west1/pipelineJobs/pipeline-pipeline-tutorial-pipeline-20220524103650
To use this PipelineJob in another session:
pipeline_job = aiplatform.PipelineJob.get('projects/968728188698/locations/europe-west1/pipelineJobs/pipeline-pipeline-tutorial-pipeline-20220524103650')
View Pipeline Job: https://console.cloud.google.com/vertex-ai/locations/europe-west1/pipelines/runs/pipeline-pipeline-tutorial-pipeline-20220524103650?project=968728188698
ℹ Pipeline dashboard at https://console.cloud.google.com/vertex-ai/locations/europe-west1/pipelines/runs/pipeline-pipeline-tutorial-pipeline-20220524103650?project=968728188698.
PipelineJob projects/968728188698/locations/europe-west1/pipelineJobs/pipeline-pipeline-tutorial-pipeline-20220524103650 current state: PipelineState.PIPELINE_STATE_RUNNING
✔ Running pipeline pipeline-tutorial-pipeline in sync mode
```

You can clearly see the url to the Vertex AI dashboard where you can inspect the pipeline execution, logs, kubeflow inputs and outputs and any logged metadata.

You may have noticed in above the line `Uploading wanna running manifest to gs://wanna-cloudlab-europe-west1/wanna-pipelines/wanna-sklearn-sample/deployment/dev/manifests/wanna-manifest.json` in the logs.
This means wanna publishes has its own pipeline manifest which allow us to run any pipeline version with any set of params.

Let's try it:

```bash
echo "eval_acc_threshold: 0.79" > pipeline/params.experiment.yaml

wanna pipeline run --manifest gs://wanna-cloudlab-europe-west1/wanna-pipelines/wanna-sklearn-sample/deployment/dev/manifests/wanna-manifest.json --params pipeline/params.experiment.yaml  --sync
```

The above snippet will run the pipeline we published earlier with a new set of params. Each manifest version is pushed to `gs://${PIPELINE_BUCKET}/pipeline-root/${PIPELINE_NAME}/deployment/release/${VERSION}/wanna_manifest.json` so it's easy to trigger these pipelines.

