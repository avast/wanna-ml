# WANNA

[![TeamCity](https://tc.ida.avast.com/app/rest/builds/buildType:BigDataSystem_Projects_Wanna_Publish___Release,branch:<default>/statusIcon)](https://tc.ida.avast.com/project/BigDataSystem_Projects_Wanna?mode=builds)
[![Artifactory](https://pypi-badger.luft.avast.com/image/pypi-local/wanna)](https://artifactory.ida.avast.com/artifactory/webapp/#/artifacts/browse/tree/General/pypi-local/wanna)

WANNA manage ML on Vertex AI :-)

## ML Pipelines

```bash
# Parses wanna, builds containers, compiles kubeflow pipeline
wanna pipeline build

# Parses wanna, builds & push containers, compiles and packages kubeflow pipeline, 
# prepares wanna-manifest.json to deploy and run pipelines
wanna pipeline push --version x.y.z

# deploys cloud scheduler and cloud function to run pipeline from wanna-manifest.json
wanna pipeline deploy --env local --version x.y.z

# runs Vertex AI Pipeline based on a wanna-manifest.json
wanna pipeline run --maniest gs://path/version/x.z/wanna-manifest.json --params path/to/params.yaml

# runs Vertex AI Pipeline based on wanna.yaml
wanna pipeline run --file path/to/wanna.yaml --sync --params path/to/params.yaml
```

### Development

### Environment setup
```bash

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

#### Editable mode
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

#### Reading
* https://python-poetry.org/
* https://pre-commit.com/
