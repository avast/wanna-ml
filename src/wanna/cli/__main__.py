from .plugins.runner import PluginRunner

runner = PluginRunner()


# required to get mkdocs to play nicely
@runner.app.callback()
def wanna():
    """
    Main entrypoint for wanna cli
    """
    runner.run()


def main() -> None:
    wanna()


if __name__ == "__main__":
    main()
