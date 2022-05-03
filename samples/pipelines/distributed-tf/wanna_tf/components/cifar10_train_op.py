from typing import NamedTuple, Dict, Optional

from kfp.v2.dsl import Dataset, component, Input, Model, Output


@component(
    base_image="gcr.io/deeplearning-platform-release/tf-cpu.2-8",
    packages_to_install=["google-cloud-aiplatform", "tensorflow", "tensorflow-io-gcs-filesystem", "tfx-bsl", "pyarrow", "tensorboard", "apache-beam", "keras-datasets"]
)
def custom_train_op(project: str,
                    location: str,
                    epoch: int,
                    training_container_uri: str,
                    display_name: str,
                    staging_bucket: str,
                    labels: Dict[str, str],
                    tensorboard: Optional[str],
                    machine_type: str,
                    accelerator_type: Optional[str],
                    accelerator_count: Optional[int],
                    service_account: str,
                    base_output_directory: str,
                    replica_count: int,
                    dataset_train: Input[Dataset],
                    dataset_test: Input[Dataset],
                    dataset_val: Input[Dataset],
                    model: Output[Model]) -> NamedTuple("outputs",
                                                [
                                                    ("model_path", str),
                                                ]):

    from collections import namedtuple
    from google.cloud.aiplatform import CustomContainerTrainingJob
    from google.cloud.aiplatform import models

    command = ["python", "/trainer/cifar10_train.py"]

    custom_job = CustomContainerTrainingJob(
        project=project,
        location=location,
        display_name=display_name,
        container_uri=training_container_uri,
        command=command,
        labels=labels,
        staging_bucket=staging_bucket,
    )

    training_args = [
        "--epoch", int(epoch),
        "--train_dataset_path", dataset_train.path,
        "--test_dataset_path", dataset_test.path,
        "--val_dataset_path", dataset_val.path,
    ]

    vertex_ai_model: Optional[models.Model] = custom_job.run(
        machine_type=machine_type,
        accelerator_type=
        accelerator_type
        if accelerator_type
        else "ACCELERATOR_TYPE_UNSPECIFIED",
        accelerator_count=
        accelerator_count
        if accelerator_type and accelerator_count
        else None,
        args=training_args,
        base_output_dir=base_output_directory,
        service_account=service_account,
        # network=instance.network,
        # environment_variables=instance.worker.env,
        replica_count=replica_count,
        # boot_disk_type=instance.worker.boot_disk_type,
        # boot_disk_size_gb=instance.worker.boot_disk_size_gb,
        # reduction_server_replica_count=instance.reduction_server.replica_count
        # if instance.reduction_server
        # else 0,
        # reduction_server_machine_type=instance.reduction_server.machine_type
        # if instance.reduction_server
        # else None,
        # reduction_server_container_uri=instance.reduction_server.container_uri
        # if instance.reduction_server
        # else None,
        # timeout=instance.timeout_seconds,
        # enable_web_access=instance.enable_web_access,
        tensorboard=tensorboard
        if tensorboard
        else None,
    )

    custom_job.wait_for_resource_creation()
    job_id = custom_job.resource_name.split("/")[-1]
    print(
        f"Training Job Dashboard in "
        f"https://console.cloud.google.com/vertex-ai/locations/{location}/training/{job_id}?project={project}"
        # noqa
    )
    custom_job.wait()

    model.name = vertex_ai_model.display_name
    model.metadata['framework'] = "TensorFlow"
    model.path = vertex_ai_model.uri

    outputs = namedtuple("outputs", ["model_path"])
    return outputs(model_path=model.path)
