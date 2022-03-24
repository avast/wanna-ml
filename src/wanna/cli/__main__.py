import typer

from .plugins.runner import PluginRunner

runner = PluginRunner()
app = typer.Typer()


# required to get mkdocs to play nicely
@app.callback()
def wanna():
    """
    Main entrypoint for wanna cli
    """
    runner.run()


def main() -> None:
    wanna()


if __name__ == "__main__":
    main()
