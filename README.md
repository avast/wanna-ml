# WANNA-ML

---

<p align="center" font-style="italic"> 
<em> Complete MLOps framework for Vertex-AI  </em>
</p>

---

<p align="center">
<a href="https://github.com/avast/wanna-ml/actions/workflows/build.yml" target="_blank">
    <img src="https://github.com/avast/wanna-ml/actions/workflows/build.yml/badge.svg" alt="Test">
</a>
<a href="https://github.com/avast/wanna-ml/actions/workflows/deploy_new_version.yml" target="_blank">
    <img src="https://github.com/avast/wanna-ml/actions/workflows/deploy_new_version.yml/badge.svg" alt="Publish">
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


## How does wanna-ml work ?

wanna-ml is a CLI tool that provides a declarative and automated approach via a single `wanna.yaml` file and grammar to generate and manage GCP Vertex AI resources, for a structured and hassle free
e2e ML experience.

Through wanna-ml you can:

* manage multiple containers built from a single place
* select different GCP profiles where resources should be created and deployed
* create, deploy, schedule, monitor and run Vertex AI pipelines from the comfort of your terminal
* create, deploy and run Vertex custom and hp tuning jobs for adhoc experiments
* create custom user or google managed Vertex AI notebooks
* create and assign tensorboard resource to your Vertex AI pipelines, notebooks or custom jobs
* remove all boilerplate to create Kubeflow components
* getting your project repository of the ground fast with pre-build templates
* what else to you wanna ?

## Help

See the [documentation](https://avast.github.io/wanna-ml/) for more details.


## Get started

* [installation](https://avast.github.io/wanna-ml/installation/) for more details.
* [get started](https://avast.github.io/wanna-ml/tutorial/) for more details.


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
