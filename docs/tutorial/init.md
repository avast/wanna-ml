---
title: WANNA Tutorial
summary: Introduction to WANNA tutorial and how to follow it
authors:
- Joao Da Silva
- Michal Mrázek
date: 2022-06-17
---

# Initializing project

Assuming you have followed the get started and have the gcloud environment setup we will need the values of `${WANNA_PROJECT_NAME}` 
and `${WANNA_GCP_PROJECT_ID}`, hand on to those. 

wanna-ml currently provides a series of cookiecutter templates to get you started:

* `blank` - empty project structure without any kubeflow components
* `sklearn` - sklearn based example using kubeflow based components

Let's get started with the blank template and answer a few questions

```bash
wanna init --template blank
```

you should see the following cookiecutter setup

```bash 
project_name [project_name]: wanna-tutorial
project_owner_fullname [project owner]: Joao Da Silva
project_owner_email [you@avast.com]: joao.silva1@avast.com
project_version [0.0.0]:
project_description [Link to MLOps project page on CML]:
project_slug [wanna_tutorial]:
project_repo_name [mlops/wanna_tutorial]:
gcp_project_id []: your-gcp-project-id
gcp_service_account []: wanna-tutorial@your-gcp-project-id.iam.gserviceaccount.com
gcp_artifact_registry_repository []: wanna-tutorial
gcp_bucket []: wanna-tutorial
```

congratulations, have a coffee you have successfully navigated the GCP and wanna-ml setup. 

We can now move on to adding our first [kubeflow component](../components.md)  

