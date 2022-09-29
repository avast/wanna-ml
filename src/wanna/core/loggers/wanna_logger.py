import logging
from typing import cast

from rich.console import Console
from rich.live import Live

if Console().encoding == "utf-8":
    in_progress_sign = ":hourglass_flowing_sand:"
    error_sign = ":x:"
    done_sign = ":white_check_mark:"
    info_sign = ":information_source:"
else:
    in_progress_sign = "(in progress)"
    error_sign = "(error)"
    done_sign = "(done)"
    info_sign = "(info)"


class Spinner(Live):
    def __init__(self, text: str, **kwargs):
        self.text = text
        super().__init__(text, **kwargs)

    def __enter__(self) -> Live:
        self.update(f"{in_progress_sign} {self.text}")
        self.start(refresh=self._renderable is not None)
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """Stops the spinner. For use in context managers."""
        if exception_value:
            self.update(f"{error_sign} {self.text}")
        else:
            self.update(f"{done_sign} {self.text}")
        self.stop()


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
        self.console = Console()

    def user_error(self, text) -> None:
        self.console.print(f"{error_sign} {text}", style="bold red")

    def user_info(self, text) -> None:
        self.console.print(f"{info_sign} {text}")

    def user_success(self, text) -> None:
        self.console.print(f"{done_sign} {text}")

    @staticmethod
    def user_spinner(text, **kwargs) -> Spinner:
        return Spinner(text=text, **kwargs)


def get_logger(name: str) -> WannaLogger:
    logging.setLoggerClass(WannaLogger)
    logger = cast(WannaLogger, logging.getLogger(name))
    return logger
