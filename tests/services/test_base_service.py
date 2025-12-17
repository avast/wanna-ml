import unittest
from unittest.mock import MagicMock, patch

from wanna.core.deployment.models import PushMode
from wanna.core.models.base_instance import BaseInstanceModel
from wanna.core.services.base import BaseService


class MockInstanceModel(BaseInstanceModel):
    """Mock instance model for testing."""

    name: str


class ConcreteService(BaseService[MockInstanceModel]):
    """Concrete implementation of BaseService for testing."""

    def _delete_one_instance(self, instance: MockInstanceModel) -> None:
        pass

    def _create_one_instance(self, instance: MockInstanceModel, **kwargs) -> None:
        pass

    def _stop_one_instance(self, instance: MockInstanceModel) -> None:
        pass

    def _return_diff(self) -> tuple[list[MockInstanceModel], list[MockInstanceModel]]:
        return ([], [])


class TestBaseService(unittest.TestCase):
    def setUp(self):
        self.service = ConcreteService(instance_type="test")
        self.instance1 = MockInstanceModel(name="instance1", project_id="test-project")
        self.instance2 = MockInstanceModel(name="instance2", project_id="test-project")
        self.service.instances = [self.instance1, self.instance2]

    @patch("wanna.core.services.base.logger")
    def test_report_method_signature(self, mock_logger):
        """Test that report method can be called with correct parameters (lines 120-121)."""
        self.service.report(
            instance_name="instance1",
            wanna_project="test-project",
            wanna_resource="notebooks",
            gcp_project="gcp-project",
            billing_id="billing-123",
            organization_id="org-456",
        )
        # Verify logger was called (method executed)
        assert mock_logger.user_info.called or mock_logger.user_success.called

    @patch("wanna.core.services.base.logger")
    def test_report_without_billing_ids(self, mock_logger):
        """Test report method when billing_id or organization_id is missing."""
        result = self.service.report(
            instance_name="instance1",
            wanna_project="test-project",
            wanna_resource="notebooks",
            gcp_project="gcp-project",
            billing_id=None,
            organization_id="org-456",
        )
        # Should return None early
        assert result is None
        mock_logger.user_error.assert_called_once()

    @patch("wanna.core.services.base.logger")
    def test_sync_method_signature(self, mock_logger):
        """Test that sync method can be called with correct parameters (lines 205-206)."""
        # Mock _return_diff to return empty lists
        self.service._return_diff = MagicMock(return_value=([], []))
        self.service.sync(force=True, push_mode=PushMode.all)
        # Verify _return_diff was called (method executed)
        self.service._return_diff.assert_called_once()

    @patch("wanna.core.services.base.logger")
    @patch("wanna.core.services.base.typer")
    def test_sync_with_force(self, mock_typer, mock_logger):
        """Test sync method with force=True."""
        to_delete = [self.instance1]
        to_create = [self.instance2]
        self.service._return_diff = MagicMock(return_value=(to_delete, to_create))
        self.service._delete_one_instance = MagicMock()
        self.service._create_one_instance = MagicMock()

        self.service.sync(force=True, push_mode=PushMode.all)

        # Verify _return_diff was called
        self.service._return_diff.assert_called_once()
        # Verify delete and create were called (force=True skips confirmation)
        self.service._delete_one_instance.assert_called_once_with(self.instance1)
        self.service._create_one_instance.assert_called_once()
