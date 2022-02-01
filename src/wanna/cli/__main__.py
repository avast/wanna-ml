from .plugins.runner import PluginRunner


runner = PluginRunner()
app = runner.app

@app.callback()
def wanna():
    """
    Main entrypoint for wanna cli 
    """
    app.run()

def main() -> None:
    wanna()

if __name__ == "__main__":
    main()
