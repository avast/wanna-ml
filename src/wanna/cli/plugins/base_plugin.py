import abc
from typing import Any, Callable, Union

import typer

CommandRegistration = Union[Callable[..., None], tuple[Callable[..., None], dict[Any, Any]]]


class BasePlugin(abc.ABC):
    """Some doc"""

    def __init__(self) -> None:
        self.app = typer.Typer()

    def register_command(self, func: CommandRegistration) -> None:
        if isinstance(func, tuple):
            self.app.command(context_settings=func[1])(func[0])
        else:
            self.app.command()(func)

    def register_many(self, funcs: list[CommandRegistration]) -> None:
        for func in funcs:
            self.register_command(func)
