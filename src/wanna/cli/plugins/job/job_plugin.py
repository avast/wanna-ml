import typer

from wanna.cli.plugins.base import BasePlugin


class JobPlugin(BasePlugin):
    def __init__(self) -> None:
        super(JobPlugin, self).__init__()
        self.secret = "some value"
        self.register_many(
            [
                self.expose_secret,
                self.expose_context,
                self.call_everything,
            ]
        )

        # add some nesting with `sub-job-command` command.
        # self.app.add_typer(SubJobPlugin().app, name='sub-job-command')

    @staticmethod
    def hello(name: str) -> None:
        typer.echo(f"Hello JobPlugin, {name}")

    @staticmethod
    def goodbye(name: str) -> None:
        typer.echo(f"Goodbye JobPlugin, {name}")

    def expose_secret(self) -> None:
        typer.echo(f"The secret is: {self.secret}")

    @staticmethod
    def expose_context(ctx: typer.Context) -> None:
        typer.echo(f"The command from context is: {ctx.command}")

    def call_everything(self, ctx: typer.Context, name: str) -> None:
        self.hello(name)
        self.expose_secret()
        self.expose_context(ctx)
        self.goodbye(name)
