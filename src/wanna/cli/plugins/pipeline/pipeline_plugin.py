import typer

from wanna.cli.plugins.base.base_plugin import BasePlugin


class PipelinePlugin(BasePlugin):
    def __init__(self) -> None:
        super(PipelinePlugin, self).__init__()
        self.secret = 14
        self.register_many(
            [
                self.expose_context,
                self.call_everything,
                self.hello,
                self.goodbye,
            ]
        )

        # add some nesting with `sub-pipeline-command` command.
        # self.app.add_typer(SubPipelinePlugin().app, name='sub-pipeline-command')

    @staticmethod
    def hello(name: str) -> None:
        typer.echo(f"Hello Pipeline, {name}")

    @staticmethod
    def goodbye(name: str) -> None:
        typer.echo(f"Goodbye Pipeline, {name}")

    @staticmethod
    def expose_context(ctx: typer.Context) -> None:
        typer.echo(f"The command from context is: {ctx.command}")

    def call_everything(self, ctx: typer.Context, name: str) -> None:
        self.hello(name)
        self.expose_context(ctx)
        self.goodbye(name)
