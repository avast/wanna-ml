import os
import unittest

from wanna.core.utils.env import (
    _cloud_build_access_allowed,
    _gcp_access_allowed,
    _should_validate,
    get_env_bool,
)


class TestEnvUtilsModel(unittest.TestCase):
    def test_get_bool_from_str(self):
        self.assertEqual(get_env_bool(value="False", fallback=True), False)
        self.assertEqual(get_env_bool(value="0", fallback=True), False)
        self.assertEqual(get_env_bool(value="false", fallback=True), False)
        self.assertEqual(get_env_bool(value="True", fallback=False), True)
        self.assertEqual(get_env_bool(value="1", fallback=False), True)
        self.assertEqual(get_env_bool(value="true", fallback=False), True)
        self.assertEqual(get_env_bool(value=None, fallback=False), False)

    def test_gcp_access_allowed_env(self):
        # Ensure GCP assess is not allowed due to `WANNA_GCP_ACCESS_ALLOWED` env
        os.environ["WANNA_GCP_ACCESS_ALLOWED"] = "False"
        self.assertEqual(_gcp_access_allowed(), False)

        os.environ["WANNA_GCP_ACCESS_ALLOWED"] = "True"
        self.assertEqual(_gcp_access_allowed(), True)

    def test_gcp_should_validate_env(self):
        # Ensure GCP validation are disabled due to `WANNA_GCP_VALIDATION_DISABLED` env
        self.assertEqual(_should_validate(), True)

        os.environ["WANNA_GCP_ENABLE_REMOTE_VALIDATION"] = "False"
        self.assertEqual(_should_validate(), False)

        os.environ["WANNA_GCP_ENABLE_REMOTE_VALIDATION"] = "True"
        self.assertEqual(_should_validate(), True)

    def test_cloud_build_access_allowed(self):
        # Ensure GCP validation are disabled due to `WANNA_GCP_CLOUD_BUILD_ACCESS_ALLOWED` env
        self.assertEqual(_cloud_build_access_allowed(), True)

        os.environ["WANNA_GCP_CLOUD_BUILD_ACCESS_ALLOWED"] = "False"
        self.assertEqual(_cloud_build_access_allowed(), False)

        os.environ["WANNA_GCP_CLOUD_BUILD_ACCESS_ALLOWED"] = "True"
        self.assertEqual(_cloud_build_access_allowed(), True)
