---
title: Troubleshooting
summary: Troubleshooting and debugging
authors:
  - Matěj Račinský
date: 2024-08-26
---

# Troubleshooting

## Stack traces
Wanna-ml CLI interface uses [typer](https://typer.tiangolo.com/) package and 
[rich](https://rich.readthedocs.io/en/latest/) for showing help, stack traces etc.

By default, the wanna-ml will show verbose stack trace containing all local variables which can simplify 
the development, but can be too verbose sometimes, 
see [the docs](https://typer.tiangolo.com/tutorial/exceptions/#exceptions-with-rich) for more details.

The stack trace looks something like this:

```
│ │            timeout = None                                                                    │ │
│ │ transcoded_request = {                                                                       │ │
│ │                      │   'uri': '/compute/v1/projects/your-gcp-project-id/regions',          │ │
│ │                      │   'query_params': ,                                                   │ │
│ │                      │   'method': 'get'                                                     │ │
│ │                      }                                                                       │ │
│ │                uri = '/compute/v1/projects/your-gcp-project-id/regions'                      │ │
│ ╰──────────────────────────────────────────────────────────────────────────────────────────────╯ │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
NotFound: 404 GET https://compute.googleapis.com/compute/v1/projects/your-gcp-project-id/regions: The resource 'projects/your-gcp-project-id' was not found
```

If you don't like this tabular stack trace, you can disable this behavior by setting environment variable

```shell
export _TYPER_STANDARD_TRACEBACK=1
```
in shell, or

```powershell
$Env:_TYPER_STANDARD_TRACEBACK=1
```
in powershell. Then, the regular stack trace will be shown, like this:
```
  File "C:\Projects\others\wanna-ml\src\wanna\core\utils\validators.py", line 29, in validate_region
    available_regions = get_available_regions(project_id=values.get("project_id"))
  File "C:\Projects\others\wanna-ml\src\wanna\core\utils\gcp.py", line 228, in get_available_regions
    response = RegionsClient(credentials=get_credentials()).list(project=project_id)
  File "C:\Users\E10270\.conda\envs\wanna-ml-py310\lib\site-packages\google\cloud\compute_v1\services\regions\client.py", line 874, in list
    response = rpc(
  File "C:\Users\E10270\.conda\envs\wanna-ml-py310\lib\site-packages\google\api_core\gapic_v1\method.py", line 131, in __call__
    return wrapped_func(*args, **kwargs)
  File "C:\Users\E10270\.conda\envs\wanna-ml-py310\lib\site-packages\google\api_core\grpc_helpers.py", line 76, in error_remapped_callable
    return callable_(*args, **kwargs)
  File "C:\Users\E10270\.conda\envs\wanna-ml-py310\lib\site-packages\google\cloud\compute_v1\services\regions\transports\rest.py", line 392, in __call__
    raise core_exceptions.from_http_response(response)
google.api_core.exceptions.NotFound: 404 GET https://compute.googleapis.com/compute/v1/projects/your-gcp-project-id/regions: The resource 'projects/your-gcp-project-id' was not found
```

If you like the verbosity of the tabular stack trace, but it's too narrow, you can increase the width to an arbitrary number by setting the `COLUMNS` or `TERMINAL_WIDTH` environment variable, e.g.:

```shell
export COLUMNS=150
export TERMINAL_WIDTH=150
```
in shell, or 
```powershell
$Env:COLUMNS=150
$Env:TERMINAL_WIDTH=150
```

Then, the stack trace will look like this:

```
│ │               self = _List(                                                                                                                    │ │
│ │                      │   _session=<google.auth.transport.requests.AuthorizedSession object at 0x000001F4E9CA17B0>,                             │ │
│ │                      │   _host='https://compute.googleapis.com',                                                                               │ │
│ │                      │   _interceptor=<google.cloud.compute_v1.services.regions.transports.rest.RegionsRestInterceptor object at               │ │
│ │                      0x000001F4E9CA15A0>                                                                                                       │ │
│ │                      )                                                                                                                         │ │
│ │            timeout = None                                                                                                                      │ │
│ │ transcoded_request = {'uri': '/compute/v1/projects/your-gcp-project-id/regions', 'query_params': , 'method': 'get'}                            │ │
│ │                uri = '/compute/v1/projects/your-gcp-project-id/regions'                                                                        │ │
│ ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯ │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
NotFound: 404 GET https://compute.googleapis.com/compute/v1/projects/your-gcp-project-id/regions: The resource 'projects/your-gcp-project-id' was not
found
```
