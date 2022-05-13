#!/usr/bin/env python

from distutils.core import setup

from setuptools import find_packages

setup(
    name="{{ cookiecutter.component_slug }}",
    version="{{ cookiecutter.component_version }}",
    description="{{ cookiecutter.component_description }}",
    author="{{ cookiecutter.component_author }}",
    author_email="{{ cookiecutter.component_author_email }}",
    url="{{ cookiecutter.component_url }}",
    python_requires=">=3.8",
    install_requires=[
        "click==8.1.3",
        "kfp==1.8.12",
        "google-cloud-aiplatform==1.13.0",
        "smart-open==6.0.0",
    ],
    include_package_data=True,
    package_dir={"": "src"},
    packages=find_packages(where="src"),
)
