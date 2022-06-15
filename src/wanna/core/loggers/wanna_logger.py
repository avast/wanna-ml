import logging
import sys
from typing import cast

import typer
from halo import Halo


class Spinner(Halo):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_tty = sys.stdout.isatty()

    def __enter__(self):
        """Starts the spinner on a separate thread. For use in context managers.
        The spinner is actually started only in the interactive terminal (tty),
        if the environment is output only, we only print the start and end of the process.

        Returns
        -------
        self
        """
        return self.start() if self.is_tty else self.info()

    def __exit__(self, exception_type, exception_value, traceback):
        """Stops the spinner. For use in context managers."""
        if exception_value:
            self.text_color = typer.colors.RED
            self.fail()
        else:
            self.text_color = typer.colors.GREEN
            self.succeed()


class WannaLogger(logging.Logger):
    """
    This Logger supports all common logging library methods
    like .info, .warning or .debug.
    On top of that, we introduce new methods for visually
    more appealing printing to users.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set the logging config here if needed
        logging.basicConfig()

    @staticmethod
    def user_error(text, fg: str = typer.colors.RED, *args, **kwargs) -> None:
        typer.secho(f"✖ {text}", fg=fg, *args, **kwargs)

    @staticmethod
    def user_info(text, *args, **kwargs) -> None:
        typer.secho(f"ℹ {text}", *args, **kwargs)

    @staticmethod
    def user_success(text, fg: str = typer.colors.GREEN, *args, **kwargs) -> None:
        typer.secho(f"✔ {text}", fg=fg, *args, **kwargs)

    @staticmethod
    def user_spinner(text, *args, **kwargs) -> Spinner:
        return Spinner(text=text, *args, **kwargs)


def get_logger(name: str) -> WannaLogger:
    logging.setLoggerClass(WannaLogger)
    logger = cast(WannaLogger, logging.getLogger(name))
    return logger
