# ignore: import-error
# pylint: disable = no-value-for-parameter
from pathlib import Path

from . import config as cfg
from google_cloud_pipeline_components.v1.bigquery import BigqueryQueryJobOp
from kfp.v2 import dsl
from kfp.v2.dsl import component


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
            project=cfg.PROJECT_ID,
            location="EU",
            query=f"""
            SELECT 
                MIN(sepal_length) AS min_length, 
                MIN(sepal_width) AS min_width, 
                MAX(sepal_length) AS max_length, 
                MAX(sepal_width) AS max_width 
            FROM  `{cfg.PROJECT_ID}`.temporary.iris
            GROUP BY class
            """,
            job_configuration_query={
                "destinationTable": {
                    "projectId": cfg.PROJECT_ID,
                    "datasetId": "temporary",
                    "tableId": "iris_stats",
                },
                "writeDisposition": "WRITE_TRUNCATE",
            },
        )
