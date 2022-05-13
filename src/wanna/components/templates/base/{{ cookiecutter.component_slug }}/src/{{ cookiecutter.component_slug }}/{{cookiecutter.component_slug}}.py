#!/usr/bin/env python3

import click
from google.cloud import aiplatform


@click.command()
@click.option(
    "--project",
    envvar="CLOUD_ML_PROJECT_ID",
)
@click.option(
    "--location",
    envvar="CLOUD_ML_REGION",
)
@click.option(
    "--experiment-name",
    envvar="EXPERIMENT_NAME",
)
def main(
    project,
    location,
    experiment_name,
):
    aiplatform.init(project=project, location=location, experiment=experiment_name)


if __name__ == "__main__":
    main()
