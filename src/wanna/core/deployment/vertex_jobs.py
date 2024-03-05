from google.cloud.aiplatform import (
    CustomContainerTrainingJob,
    CustomJob,
    CustomPythonPackageTrainingJob,
    HyperparameterTuningJob,
)
from google.cloud.aiplatform import hyperparameter_tuning as hpt

from wanna.core.deployment.artifacts_push import ArtifactsPushMixin
from wanna.core.deployment.models import JobResource
from wanna.core.loggers.wanna_logger import get_logger
from wanna.core.models.training_custom_job import (
    CategoricalParameter,
    CustomJobModel,
    DiscreteParameter,
    DoubleParameter,
    HyperParamater,
    IntegerParameter,
    TrainingCustomJobModel,
)

logger = get_logger(__name__)


class VertexJobsMixInVertex(ArtifactsPushMixin):
    def _create_hyperparameter_spec(
        self,
        parameter: HyperParamater,
    ) -> hpt._ParameterSpec:
        if isinstance(parameter, IntegerParameter) and parameter.type == "integer":
            return hpt.IntegerParameterSpec(
                min=parameter.min, max=parameter.max, scale=parameter.scale
            )
        elif isinstance(parameter, DoubleParameter) and parameter.type == "double":
            return hpt.DoubleParameterSpec(
                min=parameter.min, max=parameter.max, scale=parameter.scale
            )
        elif (
            isinstance(parameter, CategoricalParameter)
            and parameter.type == "categorical"
        ):
            return hpt.CategoricalParameterSpec(values=parameter.values)
        elif isinstance(parameter, DiscreteParameter) and parameter.type == "discrete":
            return hpt.DiscreteParameterSpec(
                values=parameter.values, scale=parameter.scale
            )
        else:
            raise ValueError(f"Unsupported parameter type {parameter.type}")

    def run_custom_job(self, manifest: JobResource[CustomJobModel], sync: bool) -> None:
        """
        Runs a Vertex AI custom job based on the provided manifest.
        If hp_tuning parameters are set, it starts a HyperParameter Tuning instead.

        Args:
            manifest (CustomJobManifest): The Job manifest to be executed
            sync (bool): Allows to run the job in async vs sync mode

        """
        custom_job = CustomJob(**manifest.job_payload)

        if manifest.job_config.hp_tuning:
            parameter_spec = {
                param.var_name: self._create_hyperparameter_spec(param)
                for param in manifest.job_config.hp_tuning.parameters
            }
            metric_spec_dict = dict()
            for key in manifest.job_config.hp_tuning.metrics:
                metric_spec_dict[key] = str(manifest.job_config.hp_tuning.metrics[key])

            runable = HyperparameterTuningJob(
                display_name=manifest.job_config.name,
                custom_job=custom_job,
                metric_spec=metric_spec_dict,
                parameter_spec=parameter_spec,
                max_trial_count=manifest.job_config.hp_tuning.max_trial_count,
                parallel_trial_count=manifest.job_config.hp_tuning.parallel_trial_count,
                search_algorithm=manifest.job_config.hp_tuning.search_algorithm,
                encryption_spec_key_name=manifest.encryption_spec,
            )
        else:
            runable = custom_job  # type: ignore

        runable.run(
            timeout=manifest.job_config.timeout_seconds,
            enable_web_access=manifest.job_config.enable_web_access,
            tensorboard=manifest.tensorboard if manifest.tensorboard else None,
            network=manifest.network,
            sync=False,
        )

        runable.wait_for_resource_creation()
        runable_id = runable.resource_name.split("/")[-1]

        if sync:
            with logger.user_spinner(
                f"Running job {manifest.job_config.name} in sync mode"
            ):
                logger.user_info(
                    f"Job Dashboard in "
                    f"https://console.cloud.google.com/vertex-ai/locations/{manifest.job_config.region}/training/{runable_id}?project={manifest.job_config.project_id}"  # noqa
                )
                custom_job.wait()
        else:
            with logger.user_spinner(
                f"Running job {manifest.job_config.name} in async mode"
            ):
                logger.user_info(
                    f"Job Dashboard in "
                    f"https://console.cloud.google.com/vertex-ai/locations/{manifest.job_config.region}/training/{runable_id}?project={manifest.job_config.project_id}"  # noqa
                )

    def run_training_job(
        self,
        manifest: JobResource[TrainingCustomJobModel],
        sync: bool,
    ):
        """
        Runs a Vertex AI training custom job based on the provided manifest
        Args:
            manifest: The training Job manifest to be executed
            sync: Allows to run the job in async vs sync mode
        """

        if manifest.job_config.worker and manifest.job_config.worker.container:
            training_job = CustomContainerTrainingJob(
                training_encryption_spec_key_name=manifest.encryption_spec,
                model_encryption_spec_key_name=manifest.encryption_spec,
                **manifest.job_payload,
            )
        elif manifest.job_config.worker and manifest.job_config.worker.python_package:
            training_job = CustomPythonPackageTrainingJob(
                training_encryption_spec_key_name=manifest.encryption_spec,
                model_encryption_spec_key_name=manifest.encryption_spec,
                **manifest.job_payload,
            )  # type: ignore
        else:
            raise ValueError(
                "Wanna could not identify the type of job. Either container or python_package"
                "must be set on the owrker"
            )

        with logger.user_spinner(f"Initiating {manifest.job_config.name} custom job"):
            logger.user_info(
                f"Outputs will be saved to {manifest.job_config.base_output_directory}"
            )
            training_job.run(
                machine_type=manifest.job_config.worker.machine_type,
                accelerator_type=manifest.job_config.worker.gpu.accelerator_type
                if manifest.job_config.worker.gpu
                and manifest.job_config.worker.gpu.accelerator_type
                else "ACCELERATOR_TYPE_UNSPECIFIED",
                accelerator_count=manifest.job_config.worker.gpu.count
                if manifest.job_config.worker.gpu
                and manifest.job_config.worker.gpu.count
                else 0,
                args=manifest.job_config.worker.args,
                base_output_dir=manifest.job_config.base_output_directory,
                service_account=manifest.job_config.service_account,
                network=manifest.network,
                environment_variables=manifest.job_config.worker.env,
                replica_count=manifest.job_config.worker.replica_count,
                boot_disk_type=manifest.job_config.worker.boot_disk.disk_type
                if manifest.job_config.worker.boot_disk
                else "pd-ssd",
                boot_disk_size_gb=manifest.job_config.worker.boot_disk.size_gb
                if manifest.job_config.worker.boot_disk
                else 100,
                reduction_server_replica_count=manifest.job_config.reduction_server.replica_count
                if manifest.job_config.reduction_server
                else 0,
                reduction_server_machine_type=manifest.job_config.reduction_server.machine_type
                if manifest.job_config.reduction_server
                else None,
                reduction_server_container_uri=manifest.job_config.reduction_server.container_uri
                if manifest.job_config.reduction_server
                else None,
                timeout=manifest.job_config.timeout_seconds,
                enable_web_access=manifest.job_config.enable_web_access,
                tensorboard=manifest.tensorboard if manifest.tensorboard else None,
                sync=False,
            )

        if sync:
            training_job.wait_for_resource_creation()
            job_id = training_job.resource_name.split("/")[-1]
            with logger.user_spinner(
                f"Running custom training job {manifest.job_config.name} in sync mode"
            ):
                logger.user_info(
                    "Job Dashboard in "
                    f"https://console.cloud.google.com/vertex-ai/locations/{manifest.job_config.region}/training/{job_id}?project={manifest.job_config.project_id}"  # noqa
                )
                training_job.wait()
        else:
            with logger.user_spinner(
                f"Running custom training job {manifest.job_config.name} in async mode"
            ):
                training_job.wait_for_resource_creation()
                job_id = training_job.resource_name.split("/")[-1]
                logger.user_info(
                    f"Job Dashboard in "
                    f"https://console.cloud.google.com/vertex-ai/locations/{manifest.job_config.region}/training/{job_id}?project={manifest.job_config.project_id}"  # noqa
                )

                # TODO:
                # Currently training_job does not release the future even with sync=False
                # and wait_for_resource_creation succeeds
                # the job is running at this stage
                # we need a "hack" to terminate main with exit 0.
