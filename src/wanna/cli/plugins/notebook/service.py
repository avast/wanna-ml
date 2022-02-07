from wanna.cli.utils.gcp.models import WannaProject, GCPSettings
from wanna.cli.plugins.notebook.models import NotebookInstance
from wanna.cli.utils import loaders
from pathlib import Path


class NotebookService:
    def __init__(
        self,
        workflow_path: Path,
    ):
        self.workflow_path = workflow_path
        self.wanna_project = None
        self.gcp_settings = None
        self.notebooks_instances = []


    def load_notebook_service(self):
        with open(self.workflow_path) as f:
            # Load workflow file
            wanna_dict = loaders.load_yaml(f, Path("."))
        self.wanna_project = WannaProject.parse_obj(wanna_dict.get("wanna_project"))
        self.gcp_settings = GCPSettings.parse_obj(wanna_dict.get("gcp_settings"))

        for nb_instance in wanna_dict.get("notebooks"):
            nb_dict = {}
            nb_dict.update(self.gcp_settings.dict())
            nb_dict.update(nb_instance)
            instance = NotebookInstance.parse_obj(nb_dict)
            self.notebooks_instances.append(instance)
