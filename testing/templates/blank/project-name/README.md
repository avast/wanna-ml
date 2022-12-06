# WANNA ML - project_name project

# Setup

```bash
# create a local env
conda create -n project-name python=3.8 poetry

# activate local env
conda activate project-name

# installs all dependencies from pyproject.toml including your project to the virtual env
poetry install

# Run any wanna-ml command
wanna --help

# runs the task `check` defined in :code:`[tool.taskipy.tasks]` in pyproject.toml
#  by default it runs linters for the code, you can modify it based on your preferences
task check

# runs the task check as well as tests and mypy via pre-commit.
task build
```


### Generating documentation

Docs use [mkdocs](https://www.mkdocs.org/)  and can be checked on localhost before pushing via `task docs-serve`. To deploy execute `task docs-deploy`
