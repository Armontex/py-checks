"""How the application sees a command."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import typer


class Registrar(Protocol):
    """A function that hangs a command on the application.

    This is the only way `_app` knows about commands: the name, the options and
    the help stay in the command's module, and the application gets a finished
    registration. The signature is the same for `app.command(...)` and for
    `app.add_typer(...)`.
    """

    def __call__(self, *, app: typer.Typer) -> None: ...
