import logging

from .plugins.runner import PluginRunner

logging.getLogger("smart_open").setLevel(logging.ERROR)
logging.getLogger("google").setLevel(logging.ERROR)
logging.getLogger("kfp").setLevel(logging.ERROR)

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
