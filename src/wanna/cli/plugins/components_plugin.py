from pathlib import Path

import typer

from wanna.cli.plugins.base_plugin import BasePlugin
from wanna.components import template


class ComponentsPlugin(BasePlugin):
    """
    Managing kubeflow components templated generation.
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
        """
        Create a kubeflow component based on a template.
        """
        template.apply(output_dir)
