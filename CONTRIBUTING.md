# Contributing

Thank you for your interest in contributing to WANNA-ML.

It is better to open an issue in the project and discuss your intention with project maintainers before you actually start implementing 
something. They can also give you tips on how to go about implementing it.

## How to Contribute

Please read the [First Contributions Guide](https://github.com/firstcontributions/first-contributions/blob/master/README.md) for general
information about contribution to OSS projects.

## Development

### Environment setup

To hack on WANNA-ML you will need `docker` daemon, a `Python >=3.7` environment setup and [gcloud cli](https://cloud.google.com/sdk/docs/install-sdk) installed

```bash

# Login to GCP
gcloud auth login
gcloud auth application-default login

# Auth against GCP docker registries
gcloud auth configure-docker europe-west1-docker.pkg.dev 
gcloud auth configure-docker europe-west3-docker.pkg.dev
 

# create a wanna work environment
conda create -n wanna python=3.8 poetry nomkl --channel conda-forge

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
