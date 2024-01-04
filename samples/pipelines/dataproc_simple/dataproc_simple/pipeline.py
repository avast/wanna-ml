# ignore: import-error
# pylint: disable = no-value-for-parameter
from pathlib import Path

from . import config as cfg
from google_cloud_pipeline_components.v1.dataproc import DataprocPySparkBatchOp
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
        DataprocPySparkBatchOp(
            # https://google-cloud-pipeline-components.readthedocs.io/en/google-cloud-pipeline-components-1.0.7/google_cloud_pipeline_components.v1.dataproc.html?highlight=dataproc%20cluster#google_cloud_pipeline_components.v1.dataproc.DataprocPySparkBatchOp
            project=cfg.PROJECT_ID,
            location=cfg.REGION,
            network_uri=cfg.DATAPROC_NETWORK,  # must have internal firewall enabled so nodes can communicate
            batch_id="dataproc-pyspark",
            container_image=cfg.DATAPROC_IMAGE_URI,
            main_python_file_uri=cfg.DATAPROC_PYSPARK_PATH,
            metastore_service=cfg.DATAPROC_METASTORE,  # must be in the same zone and network
            # spark_history_dataproc_cluster="history-dataproc-cluster" # where to store spark logs
        )
