import unittest

import pytest
from pydantic.error_wrappers import ValidationError

from wanna.cli.models.pipeline import PipelineScheduleModel


class TestPipelineModel(unittest.TestCase):
    def test_pipeline_schedule_incorrect_value(self):
        with pytest.raises(ValidationError):
            _ = PipelineScheduleModel.parse_obj(
                {
                    "cron": "bad cron schedule",
                }
            )

    def test_pipeline_schedule_correct_value(self):
        try:
            _ = PipelineScheduleModel.parse_obj(
                {
                    "cron": "0 3 * * *",
                }
            )
        except ValidationError:
            assert False, "Parsed cron schedule should be valid"
