# WANNA ML project {{ cookiecutter.project_slug }}

# Setup

```bash
# create a local env
conda create -n {{cookiecutter.project_slug}} python=3.8 poetry

# activate local env
conda activate {{cookiecutter.project_slug}}

# installs all dependencies from pyproject.toml including your project to the virtual env
poetry install

# Run any wanna-ml command
wanna --help

# runs the task `check` defined in :code:`[tool.taskipy.tasks]` in pyproject.toml
#  by default it runs linters for the code, you can modify it based on your preferences
poetry run task check

# runs the task `build`.
poetry run task build
```
