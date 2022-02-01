import typer

from wanna.cli.plugins.base import BasePlugin


class NotebookPlugin(BasePlugin):
    """
    Main entrypoint for managing Workbench Notebooks on Vertex AI
    """

    def __init__(self) -> None:
        super(NotebookPlugin, self).__init__()
        self.register_many(
            [
                self.create,
                self.destroy,
            ]
        )

        # add some nesting with `sub-notebook-command` command.
        # self.app.add_typer(SubNotebookPlugin().app, name='sub-notebook-command')

    @staticmethod
    def create(name: str) -> None:
        """
        Notebook create command
        """
        # 1. parse yaml path
        # 2. fetch notebook model
        # 2.1 check if exists and ask user for recreating or -y option by namne?
        # 3. generate config.yaml or create gcloud ai notebooks environment create
        # 4. generate script.sh
        # 5. generate gcloud command
        # 6. run gcloud command

    @staticmethod
    def destroy(name: str) -> None:
        typer.echo(f"Goodbye Notebook, {name}")
