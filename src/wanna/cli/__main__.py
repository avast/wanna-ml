from .plugins.runner import PluginRunner


def main() -> None:
    app = PluginRunner()
    app.run()


if __name__ == "__main__":
    main()
