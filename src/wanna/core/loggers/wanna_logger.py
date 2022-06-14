import logging
import sys

import typer
from halo import Halo


class Spinner(Halo):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_tty = sys.stdout.isatty()

    def __enter__(self):
        """Starts the spinner on a separate thread. For use in context managers.
        Returns
        -------
        self
        """
        return self.start() if self.is_tty else self.info()

    def __exit__(self, exception_type, exception_value, traceback):
        """Stops the spinner. For use in context managers."""
        if exception_value:
            self.text_color = "red"
            self.fail()
        else:
            self.succeed()


class WannaLogger(logging.Logger):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set the logging config here if needed
        logging.basicConfig()

    @staticmethod
    def user_error(text, *args, **kwargs) -> None:
        typer.secho(f"✖ {text}", fg=typer.colors.RED, err=True, *args, **kwargs)

    @staticmethod
    def user_info(text, *args, **kwargs) -> None:
        typer.secho(f"ℹ {text}", *args, **kwargs)

    @staticmethod
    def user_spinner(text, *args, **kwargs) -> Spinner:
        return Spinner(text=text, *args, **kwargs)
