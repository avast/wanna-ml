---
title: WANNA Profile
summary: Understanding wanna profiles
authors:
    - Joao Da Silva
    - Michal Mrázek
date: 2022-04-06
---

# WANNA Profile
We make it easy to deploy your resources to multiple environments (e.g., dev/test/prod)
with a simple change in CLI flag or with environment variable change.

WANNA Profile is a set of parameters that will cascade down to every instance you want to create
unless you overwrite them at the instance level.

### Loading WANNA Profiles
There are two possible ways to load your profile.

1. Include the `wanna_profiles` section in your main WANNA yaml config with an array of profiles
2. Include the `wanna_profiles` section in separate `profiles.yaml` saved wherever on your machine
and set env variable `WANNA_GCP_PROFILE_PATH=/path/to/your/profiles.yaml`
   
### Selecting WANNA Profile
Now that the CLI knows about your profiles, you need to select the one you want to use.
By default, the profile with the name `default` is used. You can change that with 
either `WANNA_GCP_PROFILE_NAME=my-profile-name` or `--profile=my-profile-name`.

When the selected WANNA Profile is not found, we throw an error.

### WANNA Profile parameters

::: wanna.core.models.gcp_profile.GCPProfileModel
    options:
      members: false

`wanna_profile` section of the yaml config consists of the following inputs:

- `profile_name` - name of the WANNA GCP Profile, `default` will be used if not specified otherwise.
  You could use also for example `dev`, `prod`, or any other string.
- `project_id` - GCP project id.
- `zone` - (optional) GCP location zone.
- `region` - (optional) GCP location region. If the zone is set and the region not, we automatically
  parse the region from the zone (e.g., zone `us-east1-c` automatically sets region `us-east1` if the region 
  is not supplied by the user).
- `labels` - (optional) GCP resource labels that will be added to all GCP resources you create with this profile.
  By default, we also add a few labels based on `wanna_project` section.
- `bucket` - (optional) GCS Bucket that can later be used in uploading manifests, storing logs, and so on depending
  on the resource type.
- `service_account` - (optional) GCP service account that will be used by the created resources.
If not specified, usually the default service account for each resource type is used.
  
### Example use case
```
gcp_profiles:
  - profile_name: default
    project_id: gcp-test-project
    zone: europe-west1-b
    bucket: wanna-ml-test
    labels:
      - env: test
  - profile_name: prod
    project_id: gcp-prod-project
    zone: europe-west4-a
    bucket: wanna-ml-prod
    labels:
      - env: prod
```
Now the command `wanna ...` will use the information from the `default` profile and deploy to 
`europe-west1-b`.

When you are ready with your testing, you can call `wanna ... --profile=prod` to deploy
to the production GCP project and zone `europe-west4-a`.