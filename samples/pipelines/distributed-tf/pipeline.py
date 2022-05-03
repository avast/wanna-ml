# ignore: import-error
# pylint: disable = no-value-for-parameter

# from wanna_tf.components.predictor import make_prediction_request
# from wanna_tf.components.trainer.eval_model import eval_model_op
# from wanna_tf.components.trainer.train_xgb_model import train_xgb_model_op
from kfp.v2 import dsl

import wanna_tf.config as cfg
from wanna_tf.components.cifar10_train_op import custom_train_op
from wanna_tf.components.cifar10_data_prep import data_prep_op


@dsl.pipeline(
    # A name for the pipeline. Use to determine the pipeline Context.
    name=cfg.PIPELINE_NAME,
    pipeline_root=cfg.PIPELINE_ROOT
)
def distributed_tf_sample(data_prep_mem_limit: str, train_epoch: int):
    data_prep = (
        data_prep_op()
            .set_memory_limit(data_prep_mem_limit)
            .set_display_name("Collect datasets")
    )

    # ========================================================================
    # model training
    # ========================================================================
    # train the model on Vertex AI by submitting a CustomJob
    # using the custom container (no hyper-parameter tuning)

    run_train_task = (
        custom_train_op(project=cfg.PROJECT_ID,
                        location=cfg.REGION,
                        epoch=train_epoch,
                        training_container_uri=cfg.TRAIN_IMAGE_URI,
                        display_name=cfg.MODEL_DISPLAY_NAME,
                        staging_bucket=cfg.BUCKET,
                        labels = cfg.PIPELINE_LABELS,
                        tensorboard= cfg.TENSORBOARD,
                        machine_type=cfg.MACHINE_TYPE,
                        replica_count=cfg.REPLICA_COUNT,
                        accelerator_type = cfg.ACCELERATOR_TYPE,
                        accelerator_count = cfg.ACCELERATOR_COUNT,
                        base_output_directory=cfg.PIPELINE_ROOT,
                        service_account="wanna-ml-testing@us-burger-gcp-poc.iam.gserviceaccount.com",
                        dataset_train=data_prep.outputs["dataset_train"],
                        dataset_test=data_prep.outputs["dataset_test"],
                        dataset_val=data_prep.outputs["dataset_val"])
            .set_display_name("Run custom training job")
            .after(data_prep)
    )
