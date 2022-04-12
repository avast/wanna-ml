---
title: WANNA project
summary: How to use wanna project
authors:
    - Joao Da Silva
date: 2022-04-06
---

# WANNA project
WANNA project settings sets some basic values about your project. 

`wanna_project` section of the yaml config consists of following inputs:

- `name` - name of the wanna project should be unique, this name will be used in docker service 
  for naming docker images and in labeling GCP resources. Hence it can be used also for budget monitoring.
- `version` - Currently used only in labeling GCP resources, we expect to introduce new API versions 
  and then this parameter will gain more importance. 
- `authors` - List of email addresses, currently used only in GCP resource labeling but soon also in monitoring.

### Example

```
wanna_project:
  name: wanna-julia-notebooks
  version: 1
  authors: [harry.potter@avast.com, ronald.weasley@avast.com]
```