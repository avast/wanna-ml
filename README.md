# WANNA

[![TeamCity](https://tc.ida.avast.com/app/rest/builds/buildType:BigDataSystem_Projects_Wanna_Publish___Release,branch:<default>/statusIcon)](https://tc.ida.avast.com/project/BigDataSystem_Projects_Wanna?mode=builds)
[![Artifactory](https://pypi-badger.luft.avast.com/image/pypi-local/wanna)](https://artifactory.ida.avast.com/artifactory/webapp/#/artifacts/browse/tree/General/pypi-local/wanna)

WANNA manage ML on Vertex AI :-)

### Development

### Environment setup
```bash

pip install poetry

# Install project dependencies (including dev dependencies) and load our cli  into a Python virtual environment managed by Poetry 
poetry install

# Run the cli during dev
poetry run wanna

# Run tests with pytest
poetry run pytest

# Install precommit hooks for code quality checks
poetry run pre-commit install

# Check all is good in paradise
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
