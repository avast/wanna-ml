from .plugins.runner import PluginRunner

runner = PluginRunner()
app = runner.app


def wanna():
    """
    Main entrypoint for wanna cli
    """
    app()


def main() -> None:
    wanna()


if __name__ == "__main__":
    main()
