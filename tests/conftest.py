from unittest import mock
from unittest.mock import PropertyMock

import pytest

from .mocks import mocks


# IO Mocks
@pytest.fixture(scope="session", autouse=True)
def mock_zones_client():
    with mock.patch("wanna.core.utils.gcp.ZonesClient", mocks.MockZonesClient) as _fixture:
        yield _fixture


@pytest.fixture(scope="session", autouse=True)
def mock_regions_client():
    with mock.patch("wanna.core.utils.gcp.RegionsClient", mocks.MockRegionsClient) as _fixture:
        yield _fixture


@pytest.fixture(scope="session", autouse=True)
def mock_images_client():
    with mock.patch("wanna.core.utils.gcp.ImagesClient", mocks.MockImagesClient) as _fixture:
        yield _fixture


@pytest.fixture(scope="session", autouse=True)
def mock_machine_types_client():
    with mock.patch(
        "wanna.core.utils.gcp.MachineTypesClient", mocks.MockMachineTypesClient
    ) as _fixture:
        yield _fixture


@pytest.fixture(scope="session", autouse=True)
def mock_storage_client():
    with mock.patch(
        "wanna.core.utils.validators.StorageClient", mocks.MockStorageClient
    ) as _fixture:
        yield _fixture


@pytest.fixture(scope="session", autouse=True)
def mock_upload_file():
    with mock.patch(
        "wanna.core.deployment.io.IOMixin.upload_file",
        mocks.mock_upload_file,
    ) as _fixture:
        yield _fixture


# Credentials patching
@pytest.fixture(scope="session", autouse=True)
def mock_validators_get_credentials():
    with mock.patch(
        "wanna.core.utils.validators.get_credentials",
        mocks.mock_get_credentials,
    ) as _fixture:
        yield _fixture


@pytest.fixture(scope="session", autouse=True)
def mock_gcp_get_credentials():
    with mock.patch(
        "wanna.core.utils.gcp.get_credentials",
        mocks.mock_get_credentials,
    ) as _fixture:
        yield _fixture


@pytest.fixture(scope="session", autouse=True)
def mock_deployment_get_credentials():
    with mock.patch(
        "wanna.core.deployment.credentials.get_credentials",
        mocks.mock_get_credentials,
    ) as _fixture:
        yield _fixture


@pytest.fixture(scope="session", autouse=True)
def mock_get_gcloud_user():
    with mock.patch(
        "wanna.core.utils.config_enricher.get_gcloud_user",
        mocks.mock_get_gcloud_user,
    ) as _fixture:
        yield _fixture


@pytest.fixture(scope="session", autouse=True)
def mock_verify_gcloud_presence():
    with mock.patch(
        "wanna.core.utils.gcp.verify_gcloud_presence", mocks.mock_verify_gcloud_presence
    ) as _fixture:
        yield _fixture


@pytest.fixture(scope="session", autouse=True)
def mock_config_loader_verify_gcloud_presence():
    with mock.patch(
        "wanna.core.utils.config_loader.verify_gcloud_presence", mocks.mock_verify_gcloud_presence
    ) as _fixture:
        yield _fixture


@pytest.fixture(scope="session", autouse=True)
def mock_pipeline_get_project_id():
    with mock.patch(
        "wanna.core.services.base.convert_project_id_to_project_number",
        mocks.mock_convert_project_id_to_project_number,
    ) as _fixture:
        yield _fixture


@pytest.fixture(scope="session", autouse=True)
def mock_docker_service_get_project_id():
    with mock.patch(
        "wanna.core.services.docker.convert_project_id_to_project_number",
        mocks.mock_convert_project_id_to_project_number,
    ) as _fixture:
        yield _fixture


@pytest.fixture(scope="session", autouse=True)
def mock_metrics_api():
    with mock.patch(
        "google.cloud.logging.Client.metrics_api", new_callable=PropertyMock
    ) as _fixture:
        yield _fixture


@pytest.fixture(scope="session", autouse=True)
def mock_upload_string_to_gcs():
    with mock.patch(
        "wanna.core.services.workbench_instance.upload_string_to_gcs", mocks.upload_string_to_gcs
    ) as _fixture:
        yield _fixture
