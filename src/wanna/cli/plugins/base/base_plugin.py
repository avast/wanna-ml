import abc
from typing import Callable, List

import typer


class BasePlugin(abc.ABC):
    """Some doc"""

    def __init__(self) -> None:
        self.app = typer.Typer()

    def register_command(self, func: Callable[..., None]) -> None:
        self.app.command()(func)

    def register_many(self, funcs: List[Callable[..., None]]) -> None:
        for func in funcs:
            self.register_command(func)
