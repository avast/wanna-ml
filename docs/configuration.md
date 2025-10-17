---
title: Configuration
summary: Library configuration
authors:
  - Matěj Račinský
date: 2024-01-30
---

# Configuration

## Environment variables

The library uses environment variables to configure the behavior. The following variables are available:

### Offline runs

This section is related to partial or full offline mode without actually calling GCP services.

- `WANNA_GCP_ACCESS_ALLOWED` allows communication with GCP. 
  - Default true.
  - Disable for running tests without access to the internet and off-line validations or dry-runs.
- `WANNA_GCP_ENABLE_REMOTE_VALIDATION` allows validation of GCP resources like region, machine type, etc.
  - Default true.
  - Disable for quick validation without querying GCP for list of regions or machine types.
- `WANNA_GCP_CLOUD_BUILD_ACCESS_ALLOWED` allows using cloud build instead of local docker build.
  - Default true.
  - Disable for local docker build if you can't or don't want to use the cloud build.
- `WANNA_OVERWRITE_DOCKER_IMAGE` overwrites the docker image name in the repository.
  - Default true.
  - Disable for docker image repositories which don't allow overwriting the image.
- `WANNA_ALWAYS_OVERWRITE_DOCKER_TAGS` sets which tags should be overwritten every time. Useful for e.g. `latest` tag,
which usually can be overwritten even when other tags can not. Set them as comma-separated list. This variable is used
only when `WANNA_OVERWRITE_DOCKER_IMAGE` is set to false.
  - Default `latest`.

### Docker push configuration

This section covers configuration of docker image name, including repository.

Following env vars are available. They all are optional and don't have default:

- `WANNA_DOCKER_REGISTRY_SUFFIX` optional path in the registry
- `WANNA_DOCKER_REGISTRY` overrides `docker.registry` and `gcp_profile.docker_registry` in `wanna.yaml`
  - if none are specified, the registry `{gcp_profiles.region}-docker.pkg.dev` is used.
- `WANNA_DOCKER_REGISTRY_REPOSITORY` overrides `docker.repository` and `gcp_profile.docker_repository` in `wanna.yaml`
- `WANNA_DOCKER_REGISTRY_PROJECT_ID` overrides `gcp_profiles.project_id` in `wanna.yaml`

The whole algorithm is a bit complex and can be seen in [docker.py](https://github.com/avast/wanna-ml/blob/master/src/wanna/core/services/docker.py),
but if all variables are specified, the final image name is:
```
WANNA_DOCKER_REGISTRY / WANNA_DOCKER_REGISTRY_SUFFIX / WANNA_DOCKER_REGISTRY_PROJECT_ID / WANNA_DOCKER_REGISTRY_REPOSITORY / wanna_project.name / docker.images.name
```

### Others


- `WANNA_IMPERSONATE_ACCOUNT` sets SA for impersonation
  - Required in some CI environments if the automated mechanism for impersonation does not work.
- `WANNA_GCP_PROFILE_PATH` can be used to load GCP profiles from outside of `wanna.yaml` file.
