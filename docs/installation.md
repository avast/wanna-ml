---
title: Installation
summary: Get started with wanna-ml
authors:
  - Joao Da Silva
date: 2022-04-06
---

# Installation

## Requirements
To run wanna-ml, you need `docker` daemon, a `Python >=3.7` environment setup and [gcloud cli](https://cloud.google.com/sdk/docs/install-sdk) installed

## Installing with Pipx
The recommended way to install wanna-ml is to use pipx.

pipx will install the package in isolation so you won’t have conflicts with other packages in your environment.

You can install wanna-ml like this:

```bash
pipx install wanna-ml 
```

You can upgrade the package like this:

```
pipx upgrade wanna-ml
```

if you want to manage the project with poetry

```
pipx install poetry
```

## Installing with Pip

wanna-ml is a normal Python package and you can install it with pip:

```bash
pip install wanna-ml
```

Be aware, that installing it globally might cause conflicts with other installed package.

You can solve this problem by using a pipenv environment:

```
pipenv local 3.8.12

pip install wanna-ml
```

You will need to add wanna-ml to your PATH.