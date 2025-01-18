---
title: Development
summary: Development notes
authors:
  - Matěj Račinský
date: 2024-01-07
---

# Development

## Development environment

This package uses poetry, instantiate everything by
    
```bash
poetry install --all-extras
```

in order to update dependencies, do changes in `pyproject.toml` and run

```bash
poetry lock --no-update
poetry install --all-extras
```

## Static analysis

This package uses mypy, you can run it by  
    
```bash
poetry run mypy . --config-file pyproject.toml
```

## Running all tests

To run the tests, you can use the following command:

```bash
poetry run pytest
```

this runs static analysis, linter and tests.
