import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from checksumdir import dirhash
from google.cloud.devtools import cloudbuild_v1
from google.cloud.devtools.cloudbuild_v1.services.cloud_build import CloudBuildClient
from google.cloud.devtools.cloudbuild_v1.types import Build, BuildStep, Source, StorageSource
from google.protobuf.duration_pb2 import Duration  # pylint: disable=no-name-in-module
from python_on_whales import Image, docker

from wanna.cli.models.docker import DockerBuildConfigModel, DockerImageModel, DockerModel, ImageBuildType
from wanna.cli.models.gcp_settings import GCPProfileModel
from wanna.cli.utils import loaders
from wanna.cli.utils.gcp.gcp import make_tarfile, upload_file_to_gcs
from wanna.cli.utils.spinners import Spinner
from wanna.cli.utils.templates import render_template


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
        self.image_models = docker_model.images
        self.image_store: Dict[str, Tuple[DockerImageModel, Optional[Image], str]] = {}
        self.registry = docker_model.registry or f"{gcp_profile.region}-docker.pkg.dev"
        self.repository = docker_model.repository
        self.version = version
        self.work_dir = work_dir
        self.build_dir = self.work_dir / "build" / "docker"
        self.wanna_project_name = wanna_project_name
        self.project_id = gcp_profile.project_id
        self.location = gcp_profile.region
        self.docker_build_config_path = os.getenv("WANNA_DOCKER_BUILD_CONFIG", self.work_dir / "dockerbuild.yaml")
        self.build_config = self._read_build_config(self.docker_build_config_path)
        self.cloud_build = os.getenv("WANNA_DOCKER_BUILD_IN_CLOUD", docker_model.cloud_build)
        self.bucket = gcp_profile.bucket
        self.quick_mode = quick_mode
        assert self.cloud_build or self._is_docker_client_active(), DockerClientException(
            "You need running docker client on your machine to use WANNA cli with local docker build"
        )

    def _read_build_config(self, config_path: Union[Path, str]) -> Union[DockerBuildConfigModel, None]:
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
        self, context_dir, file_path: Path, tags: List[str], docker_image_ref: str, **build_args
    ) -> Union[Image, None]:

        should_build = self._should_build_by_context_dir_checksum(self.build_dir / docker_image_ref, context_dir)

        if should_build and not self.quick_mode:

            if self.cloud_build:
                with Spinner(text=f"Building {docker_image_ref} docker image in GCP Cloud build"):
                    self._build_image_on_gcp_cloud_build(
                        context_dir=context_dir, file_path=file_path, docker_image_ref=docker_image_ref, tags=tags
                    )
                return None
            else:
                with Spinner(text=f"Building {docker_image_ref} docker image locally"):
                    image = docker.build(context_dir, file=file_path, tags=tags, **build_args)
                return image  # type: ignore
        else:
            with Spinner(
                text=f"Skipping build for context_dir={context_dir}, dockerfile={file_path} and image {tags[0]}"
            ) as s:
                s.info("Nothing has changed in the dir")
                return None

    def _pull_image(self, image_url: str) -> Union[Image, None]:
        if self.cloud_build:
            # TODO: verify that images exists remotely but dont pull them to local
            return None
        else:
            with Spinner(text="Pulling image locally"):
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
        matched_image_models = list(filter(lambda i: i.name.strip() == image_name.strip(), self.image_models))
        if len(matched_image_models) == 0:
            raise ValueError(f"No docker image with name {image_name} found")
        elif len(matched_image_models) > 1:
            raise ValueError(f"Multiple docker images with name {image_name} found, please use unique names")
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

        if docker_image_model.build_type == ImageBuildType.notebook_ready_image:
            image_name = f"{self.wanna_project_name}/{docker_image_model.name}"
            tags = self.construct_image_tag(
                registry=self.registry,
                project=self.project_id,
                repository=self.repository,
                image_name=image_name,
                versions=[self.version, "latest"],
            )
            template_path = Path("notebook_template.Dockerfile")
            shutil.copy2(
                self.work_dir / docker_image_model.requirements_txt,
                build_dir / "requirements.txt",
            )
            file_path = self._jinja_render_dockerfile(docker_image_model, template_path, build_dir=build_dir)
            context_dir = build_dir
            image = self._build_image(
                context_dir, file_path=file_path, tags=tags, docker_image_ref=docker_image_ref, **build_args
            )
        elif docker_image_model.build_type == ImageBuildType.local_build_image:
            image_name = f"{self.wanna_project_name}/{docker_image_model.name}"
            tags = self.construct_image_tag(
                registry=self.registry,
                project=self.project_id,
                repository=self.repository,
                image_name=image_name,
                versions=[self.version, "latest"],
            )
            file_path = self.work_dir / docker_image_model.dockerfile
            context_dir = self.work_dir / docker_image_model.context_dir
            image = self._build_image(
                context_dir, file_path=file_path, tags=tags, docker_image_ref=docker_image_ref, **build_args
            )
        elif docker_image_model.build_type == ImageBuildType.provided_image:
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
        excluded_files = [f"{directory}/component.yaml", f"{directory}/tests/"]

        if dockerignore.exists():
            with open(dockerignore, "r") as f:
                lines = f.readlines()
                new_files = list(map(lambda ignore: f"{directory}/{ignore.rstrip()}", lines))
                excluded_files += new_files

        excluded_files = list(set(excluded_files))
        return dirhash(directory, "sha256", excluded_files=excluded_files, excluded_extensions=["pyc", "md"])

    def _should_build_by_context_dir_checksum(self, hash_cache_dir: Path, context_dir: Path) -> bool:
        cache_file = hash_cache_dir / "cache.sha256"
        sha256hash = self._get_dirhash(context_dir)
        if cache_file.exists():
            with open(cache_file, "r") as f:
                old_hash = f.read()
                return old_hash != sha256hash
        else:
            return True

    def _write_context_dir_checksum(self, hash_cache_dir: Path, context_dir: Path):
        os.makedirs(hash_cache_dir, exist_ok=True)
        cache_file = hash_cache_dir / "cache.sha256"
        sha256hash = self._get_dirhash(context_dir)
        with open(cache_file, "w") as f:
            f.write(sha256hash)

    def _build_image_on_gcp_cloud_build(
        self, context_dir: Path, file_path: Path, tags: List[str], docker_image_ref: str
    ) -> None:
        """
        Build a docker container in GCP Cloud Build and push the images to registry.
        Folder context_dir is tarred, uploaded to GCS and then used to building.

        Args:
            context_dir: directory with all necessary files for docker image build
            file_path: path to Dockerfile
            tags:
        """

        dockerfile = os.path.relpath(file_path, context_dir)
        tar_filename = self.work_dir / f"build/docker/{docker_image_ref}.tar.gz"
        make_tarfile(context_dir, tar_filename)
        blob_name = os.path.relpath(tar_filename, self.work_dir)
        blob = upload_file_to_gcs(filename=tar_filename, bucket_name=self.bucket, blob_name=blob_name)
        tags_args = " ".join([f"-t {t}" for t in tags]).split()
        steps = BuildStep(name="gcr.io/cloud-builders/docker", args=["build", ".", "-f", dockerfile] + tags_args)

        timeout = Duration()
        timeout.seconds = 7200
        build = Build(
            source=Source(storage_source=StorageSource(bucket=blob.bucket.name, object_=blob.name)),
            steps=[steps],
            images=tags,
            timeout=timeout,
        )
        client = CloudBuildClient()
        request = cloudbuild_v1.CreateBuildRequest(
            # parent=f"projects/{self.project_id}/locations/{self.location}",
            project_id=self.project_id,
            build=build,
        )
        res = client.create_build(request=request)
        res.result()

        self._write_context_dir_checksum(self.build_dir / docker_image_ref, context_dir)

    def push_image(self, image: Image, quiet: bool = False) -> None:
        """
        Push a docker image to the registry (image must have tags)
        If you are in the cloud_build mode, nothing is pushed, images already live in cloud.
        Args:
            image: image to push
        """
        if not self.cloud_build:
            with Spinner(text=f"Pushing docker image {image.repo_tags}"):
                docker.image.push(image.repo_tags, quiet)

    def push_image_ref(self, image_ref: str, quiet: bool = False) -> None:
        """
        Push a docker image ref to the registry (image must have tags)
        Args:
            image_ref: image_ref to push
        """
        model, image, _ = self.get_image(image_ref)
        if image and model.build_type != ImageBuildType.provided_image:
            self.push_image(image)

    @staticmethod
    def remove_image(image: Image, force=False, prune=True) -> None:
        """
        Remove docker image, useful if you dont want to clutter your machine.
        """
        docker.image.remove(image, force=force, prune=prune)

    @staticmethod
    def construct_image_tag(
        registry: str, project: str, repository: str, image_name: str, versions: List[str] = ["latest"]
    ):
        """
        Construct full image tag.
        Args:
            registry:
            project:
            repository:
            image_name:
            versions:

        Returns:
            List of full image tag
        """

        return [f"{registry}/{project}/{repository}/{image_name}:{version}" for version in versions]

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
        if image_model.build_type == ImageBuildType.notebook_ready_image:
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
