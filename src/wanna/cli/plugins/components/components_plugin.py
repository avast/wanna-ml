from pathlib import Path

import typer

from wanna.cli.plugins.base.base_plugin import BasePlugin
from wanna.cli.plugins.components.service import ComponentsService


class ComponentsPlugin(BasePlugin):
    """
    Main entry point for managing Workbench Notebooks on Vertex AI
    """

    def __init__(self) -> None:
        super().__init__()
        self.register_many(
            [
                self.create,
            ]
        )

    @staticmethod
    def create(
        output_dir: Path = typer.Option(
            ...,
            "--output-dir",
            prompt="Where do you want to store the component",
            help="The output directory where wanna-ml repository will be created",
        )
    ) -> None:
        components_service = ComponentsService(output_dir)
        components_service.apply_template()
