# ignore: import-error
# pylint: disable = no-value-for-parameter

from kfp.v2 import dsl
import wanna_tf.config as cfg
from wanna_tf.components.data_prep import data_prep_op
# from wanna_tf.components.predictor import make_prediction_request
# from wanna_tf.components.trainer.eval_model import eval_model_op
# from wanna_tf.components.trainer.train_xgb_model import train_xgb_model_op
from google_cloud_pipeline_components import aiplatform as aip_components
from google_cloud_pipeline_components.experimental import custom_job


@dsl.pipeline(
    # A name for the pipeline. Use to determine the pipeline Context.
    name=cfg.PIPELINE_NAME,
    pipeline_root=cfg.PIPELINE_ROOT
)
def distributed_tf_sample(data_prep_mem_limit: str):
    data_prep = data_prep_op().set_memory_limit(data_prep_mem_limit)

    # ========================================================================
    # model training
    # ========================================================================
    # train the model on Vertex AI by submitting a CustomJob
    # using the custom container (no hyper-parameter tuning)

    # define training code arguments
    training_args = [
        "--epoch", "5",
        "--train_dataset_path", data_prep["outputs"].train_dataset_path,
        "--test_dataset_path", data_prep["outputs"].test_dataset_path,
        "--val_dataset_path", data_prep["outputs"].val_dataset_path,
    ]

    # define custom job worker_pool_specs
    worker_pool_specs = [
        {
            "machine_spec": {
                "machine_type": cfg.MACHINE_TYPE,
                "accelerator_type": cfg.ACCELERATOR_TYPE,
                "accelerator_count": cfg.ACCELERATOR_COUNT,
            },
            "replica_count": cfg.REPLICA_COUNT,
            "container_spec": {"image_uri": cfg.TRAIN_IMAGE_URI, "args": training_args},
        }
    ]

    # define custom job stage
    run_train_task = (
        custom_job.CustomTrainingJobOp(
            project=cfg.PROJECT_ID,
            location=cfg.REGION,
            display_name=cfg.MODEL_DISPLAY_NAME,
            base_output_directory=cfg.PIPELINE_ROOT,
            worker_pool_specs=worker_pool_specs,
            tensorboard=cfg.TENSORBOARD
        ).set_display_name("Run custom training job")
         .after(data_prep)
    )
