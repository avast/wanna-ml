import unittest

import pytest
from pydantic.error_wrappers import ValidationError

from wanna.core.models.cloud_scheduler import CloudSchedulerModel


class TestPipelineModel(unittest.TestCase):
    def test_pipeline_schedule_incorrect_value(self):
        with pytest.raises(ValidationError):
            _ = CloudSchedulerModel.model_validate(
                {
                    "cron": "bad cron schedule",
                }
            )

    def test_pipeline_schedule_correct_value(self):
        try:
            _ = CloudSchedulerModel.model_validate(
                {
                    "cron": "0 3 * * *",
                }
            )
        except ValidationError:
            assert False, "Parsed cron schedule should be valid"
