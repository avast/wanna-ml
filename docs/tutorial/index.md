---
title: WANNA Tutorial
summary: Introduction to WANNA tutorial and how to follow it
authors:
    - Joao Da Silva
    - Michal Mrázek
date: 2022-04-06
---

# WANNA - Get started

### Installation

Follow the suggested installation process and requirements in the [installation page in documentation](https://avast.github.io/wanna-ml/installation)

### Authentication
WANNA-ML relies on `gcloud` for user authentication. 

1. Install the `gcloud` CLI - follow [official guide](https://cloud.google.com/sdk/docs/install)
2. Authenticate with the `gcloud init`
3. Set you Google Application Credentials `gcloud auth application-default login`
4. Activate your gcp project `gcloud config set project your-gcp-project`
5. Activate or ensure activation of the following gcp apis: 
   * ```bash
      gcloud services enable \
          monitoring.googleapis.com \
          logging.googleapis.com \
          cloudbuild.googleapis.com \
          artifactregistry.googleapis.com \
          storage.googleapis.com \
          aiplatform.googleapis.com \
          notebooks.googleapis.com \
          cloudfunctions.googleapis.com \
          cloudscheduler.googleapis.com
      ```
6. export common name for the following commands:
    * ```bash
      # replace wanna-tutorial with your hyphenated lowercase name
      export WANNA_PROJECT_NAME=wanna-tutorial
      export WANNA_GCP_PROJECT_ID=your-gcp-project-id
      ```
7. Create a service account:
   * ```bash
     gcloud iam service-accounts create ${WANNA_PROJECT_NAME} \
       --description="${WANNA_PROJECT_NAME} service account" \
       --display-name="${WANNA_PROJECT_NAME}"      
     ``` 
8. Create a bucket:
    * `gsutil mb gs://${WANNA_PROJECT_NAME}`
   
9. Ensure service user can add object to bucket
   * ```bash
     gsutil iam ch serviceAccount:${WANNA_PROJECT_NAME}@${WANNA_GCP_PROJECT_ID}.iam.gserviceaccount.com:objectAdmin gs://${WANNA_GCP_PROJECT_ID}/${WANNA_PROJECT_NAME}
     ``` 

10. Add the required roles to gcp service account:
    * ```bash
      gcloud projects add-iam-policy-binding ${WANNA_GCP_PROJECT_ID} \
        --member="serviceAccount:${WANNA_PROJECT_NAME}@${WANNA_GCP_PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/aiplatform.user"
      
      gcloud projects add-iam-policy-binding ${WANNA_GCP_PROJECT_ID} \
        --member="serviceAccount:${WANNA_PROJECT_NAME}@${WANNA_GCP_PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/cloudfunctions.developer"
      
      gcloud projects add-iam-policy-binding ${WANNA_GCP_PROJECT_ID} \
        --member="serviceAccount:${WANNA_PROJECT_NAME}@${WANNA_GCP_PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/cloudscheduler.admin"

      gcloud projects add-iam-policy-binding ${WANNA_GCP_PROJECT_ID} \
        --member="serviceAccount:${WANNA_PROJECT_NAME}@${WANNA_GCP_PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/artifactregistry.writer"
      
      gcloud projects add-iam-policy-binding ${WANNA_GCP_PROJECT_ID} \
        --member="serviceAccount:${WANNA_PROJECT_NAME}@${WANNA_GCP_PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/notebooks.admin"
            
      gcloud projects add-iam-policy-binding ${WANNA_GCP_PROJECT_ID} \
        --member="serviceAccount:${WANNA_PROJECT_NAME}@${WANNA_GCP_PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/iam.serviceAccountTokenCreator"
      
      gcloud projects add-iam-policy-binding ${WANNA_GCP_PROJECT_ID} \
        --member="serviceAccount:${WANNA_PROJECT_NAME}@${WANNA_GCP_PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/iam.serviceAccountUser"
      ``` 

11. Create Artifact registry docker repository
    * ```bash
      gcloud artifacts repositories create ${WANNA_PROJECT_NAME} \
        --repository-format=docker \
        --location=europe-west1 \
        --description="${WANNA_PROJECT_NAME} docker registry" 
      ```

12. Authenticate GCP artifact registry
    * ```bash
      gcloud auth configure-docker europe-west1-docker.pkg.dev 
      ```

13. Enable service account for wanna
    * ```bash 
      gcloud config set auth/impersonate_service_account ${WANNA_PROJECT_NAME}@${WANNA_GCP_PROJECT_ID}.iam.gserviceaccount.com 
      ```

### Docker Build
You can use a local Docker daemon to build Docker images, but it is not required. 
You are free to choose between local building on GCP Cloud Build. 
If you prefer local Docker image building, install  [Docker Desktop](https://www.docker.com/products/docker-desktop/).

### GCP IAM Roles and Permissions
Different WANNA-ML calls require different GCP permissions to create given resources on GCP. Our [documentation page](https://avast.github.io/wanna-ml/)
lists recommended GCP IAM roles for each `wanna` command.

