import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from caseconverter import kebabcase
from dirhash import dirhash
from google.api_core.client_options import ClientOptions
from google.api_core.future.polling import DEFAULT_POLLING
from google.api_core.operation import Operation
from google.cloud.devtools import cloudbuild_v1
from google.cloud.devtools.cloudbuild_v1.services.cloud_build import CloudBuildClient
from google.cloud.devtools.cloudbuild_v1.types import (
    Build,
    BuildOptions,
    BuildStep,
    Source,
    StorageSource,
)
from google.protobuf.duration_pb2 import Duration  # pylint: disable=no-name-in-module
from python_on_whales import Image, docker

from wanna.core.deployment.models import PushMode
from wanna.core.loggers.wanna_logger import get_logger
from wanna.core.models.docker import (
    DockerBuildConfigModel,
    DockerImageModel,
    DockerModel,
    ImageBuildType,
    LocalBuildImageModel,
    NotebookReadyImageModel,
    ProvidedImageModel,
)
from wanna.core.models.gcp_profile import GCPProfileModel
from wanna.core.utils import loaders
from wanna.core.utils.credentials import get_credentials
from wanna.core.utils.env import cloud_build_access_allowed, gcp_access_allowed
from wanna.core.utils.gcp import (
    convert_project_id_to_project_number,
    make_tarfile,
    upload_file_to_gcs,
)
from wanna.core.utils.templates import render_template

logger = get_logger(__name__)


class DockerClientException(Exception):
    pass


class DockerService:
    def __init__(
        self,
        docker_model: DockerModel,
        gcp_profile: GCPProfileModel,
        version: str,
        work_dir: Path,
        wanna_project_name: str,
        quick_mode: bool = False,  # just returns tags but does not build
    ):
        self.docker_model = docker_model
        self.image_models = docker_model.images
        self.image_store: Dict[str, Tuple[DockerImageModel, Optional[Image], str]] = {}

        # Artifactory mirrors to different registry/projectid/repository combo
        registry_suffix = os.getenv("WANNA_DOCKER_REGISTRY_SUFFIX")
        self.docker_registry_suffix = f"{registry_suffix}/" if registry_suffix else ""
        self.docker_registry = (
            os.getenv("WANNA_DOCKER_REGISTRY")
            or docker_model.registry
            or gcp_profile.docker_registry
            or f"{gcp_profile.region}-docker.pkg.dev"
        )
        docker_repository = (
            os.getenv("WANNA_DOCKER_REGISTRY_REPOSITORY") or docker_model.repository
        )
        self.docker_repository = (
            docker_repository if docker_repository else gcp_profile.docker_repository
        )
        self.docker_project_id = (
            os.getenv("WANNA_DOCKER_REGISTRY_PROJECT_ID") or gcp_profile.project_id
        )

        self.version = version
        self.work_dir = work_dir
        self.build_dir = self.work_dir / "build" / "docker"
        self.wanna_project_name = wanna_project_name
        self.project_id = gcp_profile.project_id
        self.location = gcp_profile.region
        self.docker_build_config_path = os.getenv(
            "WANNA_DOCKER_BUILD_CONFIG", self.work_dir / "dockerbuild.yaml"
        )
        self.build_config = self._read_build_config(self.docker_build_config_path)
        self.cloud_build_timeout = docker_model.cloud_build_timeout
        self.cloud_build = (
            False
            if not gcp_access_allowed or not cloud_build_access_allowed
            else docker_model.cloud_build
        )

        self.cloud_build_workerpool = docker_model.cloud_build_workerpool
        self.cloud_build_workerpool_location = (
            docker_model.cloud_build_workerpool_location or self.location
        )
        self.bucket = gcp_profile.bucket
        self.quick_mode = quick_mode
        assert (
            self.cloud_build or self._is_docker_client_active()
        ), DockerClientException(
            "You need running docker client on your machine to use WANNA cli with local docker build"
        )

    def _read_build_config(
        self, config_path: Union[Path, str]
    ) -> Union[DockerBuildConfigModel, None]:
        """
        Reads the DockerBuildConfig from local file.
        If the file does not exist, return None.

        Args:
            config_path:

        Returns:
            DockerBuildConfigMode
        """
        if os.path.isfile(config_path):
            with open(config_path) as file:
                # Load workflow file
                build_config_dict = loaders.load_yaml(file, self.work_dir)
            build_config = DockerBuildConfigModel.parse_obj(build_config_dict)
            return build_config
        return None

    @staticmethod
    def _is_docker_client_active() -> bool:
        """
        Method to find out if you have a running docker client on your machine.

        Returns:
            True if docker client found, False otherwise
        """
        return docker.info().id is not None

    def _build_image(
        self,
        context_dir,
        file_path: Path,
        tags: List[str],
        docker_image_ref: str,
        **build_args,
    ) -> Union[Image, None]:
        should_build = self._should_build_by_context_dir_checksum(
            self.build_dir / docker_image_ref, context_dir
        )

        if should_build and not self.quick_mode:
            if self.cloud_build:
                logger.user_info(
                    text=f"Building {docker_image_ref} docker image in GCP Cloud build"
                )
                op = self._build_image_on_gcp_cloud_build(
                    context_dir=context_dir,
                    file_path=file_path,
                    docker_image_ref=docker_image_ref,
                    tags=tags,
                )
                project = convert_project_id_to_project_number(self.project_id)
                build_id = op.metadata.build.id
                base = "https://console.cloud.google.com/cloud-build/builds"
                if self.cloud_build_workerpool:
                    link = (
                        base
                        + f";region={self.cloud_build_workerpool_location}/{build_id}?project={project}"
                    )
                else:
                    link = base + f"/{build_id}?project={project}"
                try:
                    op.result()
                    self._write_context_dir_checksum(
                        self.build_dir / docker_image_ref, context_dir
                    )
                except:
                    raise Exception(f"Build failed. Here is a link to the logs: {link}")
                return None
            else:
                logger.user_info(
                    text=f"Building {docker_image_ref} docker image locally with {build_args}"
                )
                image = docker.build(
                    context_dir, file=file_path, load=True, tags=tags, **build_args
                )
                self._write_context_dir_checksum(
                    self.build_dir / docker_image_ref, context_dir
                )
                return image  # type: ignore
        else:
            logger.user_info(
                text=f"Skipping build for context_dir={context_dir}, dockerfile={file_path} and image {tags[0]}"
            )
            return None

    def _pull_image(self, image_url: str) -> Union[Image, None]:
        if self.cloud_build or self.quick_mode:
            # TODO: verify that images exists remotely but dont pull them to local
            return None
        else:
            with logger.user_spinner("Pulling image locally"):
                image = docker.pull(image_url, quiet=True)
            return image  # type: ignore

    def find_image_model_by_name(self, image_name: str) -> DockerImageModel:
        """
        Finds a DockerImageModel with given image_name from self.image_models
        Args:
            image_name: name to find

        Returns:
            DockerImageModel
        """
        matched_image_models = list(
            filter(lambda i: i.name.strip() == image_name.strip(), self.image_models)
        )
        if len(matched_image_models) == 0:
            raise ValueError(f"No docker image with name {image_name} found")
        elif len(matched_image_models) > 1:
            raise ValueError(
                f"Multiple docker images with name {image_name} found, please use unique names"
            )
        else:
            return matched_image_models[0]

    def get_image(
        self,
        docker_image_ref: str,
    ) -> Tuple[DockerImageModel, Optional[Image], str]:
        """
        A wrapper around _get_image that checks if the docker image has been already build / pulled
        and cached in image_store.
        """
        if docker_image_ref in self.image_store:
            image = self.image_store.get(docker_image_ref)
            return image  # type: ignore
        else:
            image = self._get_image(
                docker_image_ref=docker_image_ref,
            )
            self.image_store.update({docker_image_ref: image})
            return image

    def _get_image(
        self,
        docker_image_ref: str,
    ) -> Tuple[DockerImageModel, Optional[Image], str]:
        """
        Given the docker_image_ref, this function prepares the image for you.
        Depending on the build_type, it either build the docker image or
        if you work with provided_image type, it will pull the image to verify the url.
        Args:
            docker_image_ref:

        Returns:

        """
        docker_image_model = self.find_image_model_by_name(docker_image_ref)

        build_dir = self.work_dir / Path("build") / "docker" / docker_image_model.name
        os.makedirs(build_dir, exist_ok=True)
        build_args = self.build_config.dict() if self.build_config else {}

        if isinstance(docker_image_model, NotebookReadyImageModel):
            tags = self.construct_image_tag(
                image_name=docker_image_model.name,
            )
            template_path = Path("notebook_template.Dockerfile")
            shutil.copy2(
                self.work_dir / docker_image_model.requirements_txt,
                build_dir / "requirements.txt",
            )
            file_path = self._jinja_render_dockerfile(
                docker_image_model, template_path, build_dir=build_dir
            )
            context_dir = build_dir
            image = self._build_image(
                context_dir,
                file_path=file_path,
                tags=tags,
                docker_image_ref=docker_image_ref,
                **build_args,
            )
        elif isinstance(docker_image_model, LocalBuildImageModel):
            tags = self.construct_image_tag(
                image_name=docker_image_model.name,
            )
            file_path = self.work_dir / docker_image_model.dockerfile
            context_dir = self.work_dir / docker_image_model.context_dir
            image = self._build_image(
                context_dir,
                file_path=file_path,
                tags=tags,
                docker_image_ref=docker_image_ref,
                **build_args,
            )
        elif isinstance(docker_image_model, ProvidedImageModel):
            image = self._pull_image(docker_image_model.image_url)
            tags = [docker_image_model.image_url]
        else:
            raise Exception("Invalid image model type.")

        return (
            docker_image_model,
            image,
            tags[0],
        )

    def _get_dirhash(self, directory: Path):
        dockerignore = directory / ".dockerignore"
        ignore = []

        if dockerignore.exists():
            with open(dockerignore, "r") as f:
                lines = f.readlines()
                ignore += [
                    ignore.rstrip()
                    for ignore in lines
                    if not ignore.startswith("#") and not ignore.strip() == ""
                ]

        return dirhash(directory, "sha256", ignore=set(ignore))

    def _get_cache_path(self, hash_cache_dir: Path):
        version = kebabcase(self.version)
        os.makedirs(hash_cache_dir, exist_ok=True)
        return (
            hash_cache_dir
            / f"{kebabcase(self.docker_repository)}-{version}-cache.sha256"
        )

    def _should_build_by_context_dir_checksum(
        self, hash_cache_dir: Path, context_dir: Path
    ) -> bool:
        cache_file = self._get_cache_path(hash_cache_dir)
        sha256hash = self._get_dirhash(context_dir)
        if cache_file.exists():
            with open(cache_file, "r") as f:
                old_hash = f.read().replace("\n", "")
                return old_hash != sha256hash
        else:
            return True

    def _write_context_dir_checksum(self, hash_cache_dir: Path, context_dir: Path):
        cache_file = self._get_cache_path(hash_cache_dir)
        sha256hash = self._get_dirhash(context_dir)
        with open(cache_file, "w") as f:
            f.write(sha256hash)

    def _build_image_on_gcp_cloud_build(
        self, context_dir: Path, file_path: Path, tags: List[str], docker_image_ref: str
    ) -> Operation:
        """
        Build a docker container in GCP Cloud Build and push the images to registry.
        Folder context_dir is tarred, uploaded to GCS and then used to building.

        Args:
            context_dir: directory with all necessary files for docker image build
            file_path: path to Dockerfile
            tags:
        """

        dockerfile = os.path.relpath(file_path, context_dir)
        tar_filename = self.work_dir / "build" / "docker" / f"{docker_image_ref}.tar.gz"
        make_tarfile(context_dir, tar_filename)
        blob_name = os.path.relpath(tar_filename, self.work_dir).replace("\\", "/")
        blob = upload_file_to_gcs(
            filename=tar_filename, bucket_name=self.bucket, blob_name=blob_name
        )
        tags_args = " ".join([f"--destination={t}" for t in tags]).split()

        steps = BuildStep(
            name=f"gcr.io/kaniko-project/executor:{self.docker_model.cloud_build_kaniko_version}",
            args=tags_args
            + self.docker_model.cloud_build_kaniko_flags
            + ["--dockerfile", dockerfile],
        )

        timeout = Duration()
        timeout.seconds = self.cloud_build_timeout

        # Set the pooling timeout to self.cloud_build_timeout seconds
        # since often large GPUs builds exceed the 900s limit
        DEFAULT_POLLING._timeout = self.cloud_build_timeout

        if self.cloud_build_workerpool:
            project_number = convert_project_id_to_project_number(self.project_id)
            options = BuildOptions(
                pool=BuildOptions.PoolOption(
                    name=f"projects/{project_number}/locations/{self.cloud_build_workerpool_location}"
                    f"/workerPools/{self.cloud_build_workerpool}"
                )
            )
            api_endpoint = (
                f"{self.cloud_build_workerpool_location}-cloudbuild.googleapis.com"
            )
        else:
            options = None
            api_endpoint = "cloudbuild.googleapis.com"

        build = Build(
            source=Source(
                storage_source=StorageSource(bucket=blob.bucket.name, object_=blob.name)
            ),
            steps=[steps],
            # Issue with kaniko builder, images wont show in cloud build artifact column in UI
            # https://github.com/GoogleCloudPlatform/cloud-builders-community/issues/212
            # images=tags,
            timeout=timeout,
            options=options,
        )
        client = CloudBuildClient(
            credentials=get_credentials(),
            client_options=ClientOptions(api_endpoint=api_endpoint),
        )
        request = cloudbuild_v1.CreateBuildRequest(
            project_id=self.project_id,
            build=build,
        )
        return client.create_build(request=request)

    def push_image(
        self, image_or_tags: Union[Image, List[str]], quiet: bool = False
    ) -> None:
        """
        Push a docker image to the registry (image must have tags)
        If you are in the cloud_build mode, nothing is pushed, images already live in cloud.
        Args:
            :param image_or_tags:
            :param quiet:
        """
        if not self.cloud_build:
            tags = (
                image_or_tags.repo_tags
                if isinstance(image_or_tags, Image)
                else image_or_tags
            )
            logger.user_info(text=f"Pushing docker image {tags}")
            docker.image.push(tags, quiet)

    def push_image_ref(
        self, image_ref: str, quiet: bool = False  # noqa: ARG002
    ) -> None:
        """
        Push a docker image ref to the registry (image must have tags)
        Args:
            image_ref: image_ref to push
            quiet: If you don't want to see the progress bars.
        """
        model, image, tag = self.get_image(image_ref)
        if (image or tag) and model.build_type != ImageBuildType.provided_image:
            self.push_image(image or [tag])

    @staticmethod
    def remove_image(image: Image, force=False, prune=True) -> None:
        """
        Remove docker image, useful if you dont want to clutter your machine.
        """
        docker.image.remove(image, force=force, prune=prune)

    def construct_image_tag(
        self,
        image_name: str,
    ):
        """
        Construct full image tag.
        Args:
            image_name:

        Returns:
            List of full image tag
        """
        versions = [self.version, "latest"]
        return [
            f"{self.docker_registry}/{self.docker_registry_suffix}{self.docker_project_id}/"
            f"{self.docker_repository}/{self.wanna_project_name}/{image_name}:{version}"
            for version in versions
        ]

    def build_container_and_get_image_url(
        self, docker_image_ref: str, push_mode: PushMode = PushMode.all
    ) -> str:
        if push_mode == PushMode.quick:
            # only get image tag
            docker_image_model = self.find_image_model_by_name(docker_image_ref)
            tags = self.construct_image_tag(image_name=docker_image_model.name)
            image_url = tags[0]
        elif push_mode == PushMode.manifests:
            # only build image
            image_tag = self.get_image(docker_image_ref=docker_image_ref)
            image_url = image_tag[2]
        else:
            # build image and push
            image_tag = self.get_image(docker_image_ref=docker_image_ref)
            if len(image_tag) > 1 and image_tag[1]:
                self.push_image(image_tag[1])
            image_url = image_tag[2]
        return image_url

    @staticmethod
    def _jinja_render_dockerfile(
        image_model: DockerImageModel,
        template_path: Path,
        build_dir: Path,
    ) -> Path:
        """
        Based on image_model.type, we render dockerfile for this image type.
        Args:
            image_model: docker image model
            template_path: path to the dockerfile jinja template
            build_dir: build directory (where to save rendered dockerfile)

        Returns:
            path to the rendered dockerfile
        """
        if isinstance(image_model, NotebookReadyImageModel):
            rendered = render_template(
                source_path=template_path,
                base_image=image_model.base_image,
                requirements_txt=image_model.requirements_txt,
            )
        else:
            raise Exception("Invalid docker image type.")
        docker_file_path = build_dir / Path(f"{image_model.name}.Dockerfile")
        with open(docker_file_path, "w") as file:
            file.write(rendered)
        return docker_file_path
