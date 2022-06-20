---
title: WANNA Kubeflow components
summary: Generating Kubeflow components
authors:
- Joao Da Silva
- Michal Mrázek
  date: 2022-06-17
---

# WANNA Component generator

Vertex AI ML Pipelines are based on Kubeflow pipelines V2 API and prepare the recommended kubeflow components layout can
be repetitive and take some doing. `wanna-ml` has a component generator to get you off the ground quickly.

### Create first component for data prep
The first component we will create is a data component where we can do some data preparation for the rest of the pipeline.

Lets run `wanna components create --output-dir pipeline/components/`, fill in the template generator and verify that the output should be something like.

```bash

component_name [component_name]: data
component_author [component author]: Joao Da Silva
component_author_email [you@avast.com]: joao.silva1@avast.com
component_version [0.0.0]: 
component_description [Describe your component]: data component for WANNA pipeline tutorial        
component_url [Link to MLOps project page on CML]: 
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

You may also notice that a Dockerfile is present and here is where the python data `lib` is installed and executed. 
However, we do need to add this Dockerfile to `wanna.yaml` so that wanna knows about it and can build it and export it.

Update wanna `docker.images` yaml array with

```bash
images
    - build_type: local_build_image
      name: data
      context_dir: pipeline/components/data/
      dockerfile: pipeline/components/data/Dockerfile
``` 

and add the docker ref `data` into the pipeline in wanna.yaml so that wanna can build the container, and expose the docker tag to the kubeflow pipeline at compile time. 

Update wanna.yaml path `pipelines[0].docker_image_ref` with `docker_image_ref: [data]`.

It should now look like:

```bash
pipelines:
  - name: wanna-tutorial-pipeline
    bucket: gs://wanna-tutorial
    pipeline_file: pipeline/pipeline.py
    pipeline_params: pipeline/params.yaml
    docker_image_ref: ["data"]
    tensorboard_ref: wanna-tutorial-board
```

Earlier I mentioned `expose the docker tag`, this means wanna exports every docker tag from `docker.images` array as `${NAME_DOCKER_URI}` so in this component you can see in the yaml `${DATA_DOCKER_URI}` which gets replaced at compile time, 
this way we have the possibility to have dynamic Kubeflow components versioned according to current pipeline release.

Next we may want to make this component part of our `poetry` build so that we can run tests, linter and whatnot from a single place.

Lets edit our `pyproject.toml` as follows:

```toml
[tool.poetry.dependencies]
python = ">=3.7,<3.11"
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

You can now see that you have a self-contained, testable component ready to be added to our kubeflow pipeline in `pipeline/pipeline.py`

