# ignore: import-error
# pylint: disable = no-value-for-parameter
from pathlib import Path

from . import config as cfg
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
def wanna_pipeline(eval_acc_threshold: float):
    pipeline_dir = Path(__file__).parent.resolve()

    # ===================================================================
    # Get pipeline result notification
    # ===================================================================
    exit_task = (
        on_exit().set_display_name("On Exit Dummy Task").set_caching_options(False)
    )

    with dsl.ExitHandler(exit_task):
        pass
