# ignore: import-error
# pylint: disable = no-value-for-parameter
from pathlib import Path

import config as cfg
from kfp.v2 import dsl
from kfp.v2.dsl import component

from google_cloud_pipeline_components.v1.bigquery import BigqueryQueryJobOp


@component(
    base_image="python:3.9",
)
def on_exit():
    import logging

    logging.getLogger().setLevel(logging.INFO)

    logging.info("This Component will run on exit, as last")


@dsl.pipeline(
    # A name for the pipeline. Use to determine the pipeline Context.
    name=cfg.PIPELINE_NAME,
    pipeline_root=cfg.PIPELINE_ROOT,
)
def wanna_pipeline():
    pipeline_dir = Path(__file__).parent.resolve()

    # ===================================================================
    # Get pipeline result notification
    # ===================================================================
    exit_task = (
        on_exit().set_display_name("On Exit Dummy Task").set_caching_options(False)
    )

    with dsl.ExitHandler(exit_task):
        bq_table = BigqueryQueryJobOp(
            # https://google-cloud-pipeline-components.readthedocs.io/en/google-cloud-pipeline-components-1.0.0/google_cloud_pipeline_components.v1.bigquery.html#google_cloud_pipeline_components.v1.bigquery.BigqueryQueryJobOp
            project="us-burger-gcp-poc",
            location="EU",
            query="""
            SELECT 
                MIN(sepal_length) AS min_length, 
                MIN(sepal_width) AS min_width, 
                MAX(sepal_length) AS max_length, 
                MAX(sepal_width) AS max_width 
            FROM  `us-burger-gcp-poc`.temporary.iris
            GROUP BY class
            """,
            job_configuration_query={
                "destinationTable": {
                    "projectId": "us-burger-gcp-poc",
                    "datasetId": "temporary",
                    "tableId": "iris_stats",
                },
                "writeDisposition": "WRITE_TRUNCATE",
            },
        )
