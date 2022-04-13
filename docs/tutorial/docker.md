---
title: WANNA Docker
summary: How to use wanna docker service
authors:
    - Joao Da Silva
    - Michal Mrázek
date: 2022-04-06
---

# WANNA Docker
Multiple resources created by WANNA rely on Docker containers. We make it easy for you to
build your images either locally or using GCP Cloud Build. However, the GCP Cloud Build will
not be allowed to use in production.


### Types of docker images
We currently support three types of docker images:

- `provided_image` - you supply a link to docker image in the registry. Wo don't build anything,
  just redirect this link to GCP.
- `local_build_image` - you supply a Dockerfile with context directory and additional information.
  We build the image for you on your machine or in cloud.
- `notebook_ready_image` - you supply a list of pip requirements to install in your Jupyter Notebook.
This is useful if you want to start a notebook with custom libraries but you dont want to handle
  Dockerfile information.
  
### Referencing docker images
Each docker images must have a `name`. By this name, you can later reference it in 
resource configuration, usually as `docker_image_ref`.

Example:
```
docker:
  images:
    - build_type: local_build_image
      name: custom-notebook-container-julia
      context_dir: .
      dockerfile: Dockerfile.notebook
  repository: wanna-samples
  cloud_build: true
  
notebooks:
  - name: wanna-notebook-julia
    environment:
      docker_image_ref: custom-notebook-container-julia
```

### Local build vs GCP Cloud Build
By default, all docker images are build locally on your machine and then pushed to registry.
For faster testing lifecycle you can build images directly using GCP Cloud Build. 
Only needed change is to set `cloud_build: true` in `docker` section of WANNA yaml config
or set `WANNA_DOCKER_BUILD_IN_CLOUD=true` (env variable takes precedence).

Building in cloud is generally faster as the docker images are automatically already in registry
and there is no need to push the images over the network. That makes it suitable for fast testing. 
However, building images in cloud is not allowed for production.

### Build configuration
When building locally, we offer you a way to set additional build parameters. These parameters
must be specified in separate yaml file in path `WANNA_DOCKER_BUILD_CONFIG`. If this is not set,
it defaults to the `dockerbuild.yaml` in working directory.

You can set:

- `build_args: Dict[str, str]` 
- `labels: Dict[str, str]`
- `network: Optional[str]`
- `platforms: Optional[List[str]]`
- `secrets: Union[str, List[str]]`
- `ssh: Optional[str]`
- `target: Optional[str]`

These parameters refer to [standard docker build parameters](https://github.com/docker/buildx#buildx-bake-options-target).
  
One example usecase can be when you want to git clone your internal repository during
the docker build.

In the `dockerbuild.yaml`:
```
ssh: github=~/.ssh/id_rsa
```

In the `Dockerfile`:
```
RUN mkdir -m 700 /root/.ssh; \
  touch -m 600 /root/.ssh/known_hosts; \
  ssh-keyscan git.int.avast.com > /root/.ssh/known_hosts

RUN --mount=type=ssh,id=github git clone git@git.your.company.com:your_profile/your_repo.git
```

### Parameters for docker section
docker section takes following paremeters:
- `images` - list of docker images, see below
- `repository`- GCP Artifact Registry repository for pushing images
- `registry`- (optional) GCP Artifact Registry, when not set it defaults to `{gcp_profile.region}-docker.pkg.dev`
- `cloud_build` - `false` (default) to build locally, `true` to use GCP Cloud Build  


#### Provided image parameters:
- `build_type: provided_image`
- `name` - this will later be used in `docker_image_ref` in other resources
- `image_url` - link to the image

#### Local build image parameters:
- `build_type: local_build_image`
- `name` - this will later be used in `docker_image_ref` in other resources
- `build_args` - (optional) docker build args
- `context_dir` - Path to the docker build context directory
- `dockerfile` - Path to the Dockerfile

#### Notebook ready image:
- `build_type: notebook_ready_image`
- `name` - this will later be used in `docker_image_ref` in other resources
- `build_args` - (optional) docker build args
- `base_image` - (optional) base notebook docker image, you can check available images [here](https://cloud.google.com/deep-learning-vm/docs/images)
  when not set, it defaults to standard base CPU notebook.
- `requirements_txt` - Path to the `requirements.txt` file


### Roles and permissions
Permission and suggested roles (applying the principle of least privilege) required for docker images manipulation:

| WANNA action  | Permissions | Suggested Roles  |
| -----------   | ----------- | ------ |
| build in Cloud Build  | `cloudbuild.builds.create` and [more](https://cloud.google.com/build/docs/iam-roles-permissions)       | ` roles/cloudbuild.builds.builder`     |
| push  | `artifactregistry.repositories.uploadArtifacts`, `artifactregistry.tags.create`, `artifactregistry.tags.update`      | `roles/artifactregistry.writer`       |

For building the docker images locally, you will need the permission for push to GCP as described above and running local Docker daemon.
You also have to authenticate docker with GCP, detailed documentation is [here](https://cloud.google.com/artifact-registry/docs/docker/authentication).
But generally you should be fine with running:

```bash
gcloud auth login

gcloud auth configure-docker europe-west1-docker.pkg.dev # Add more comma-separated repository hostnames if you wish
```

[Full list of available roles and permission.](https://cloud.google.com/build/docs/iam-roles-permissions)
