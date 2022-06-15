from typing import Any

from wanna.core.deployment.vertex_connector import VertexConnector


class TestGCPConnector:
    def setup(self) -> None:
        self.project_id = "gcp-project"
        self.zone = "us-east1-a"
        self.connector = VertexConnector[Any]()

    def test_upsert_cloud_function(self):
        # self.connector.upsert_cloud_function()
        pass

    def test_upsert_cloud_scheduler(self):
        # self.connector.upsert_cloud_scheduler()
        pass

    def upsert_alert_policy(self):
        # self.connector.upsert_alert_policy()
        pass

    def test_upsert_log_metric(self):
        # self.connector.upsert_log_metric()
        pass

    def test_deploy_pipeline(self):
        # self.connector.deploy_pipeline()
        pass

    def test_run_pipeline(self):
        # self.connector.run_pipeline()
        pass

    def test_deploy_job(self):
        # self.connector.deploy_job()
        pass

    def test_run_job(self):
        # self.connector.run_job()
        pass

    def test_push_artifacts(self):
        # self.connector.push_artifacts()
        pass
