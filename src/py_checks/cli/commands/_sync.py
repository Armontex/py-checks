"""The `sync` command: build the configs that depend on the project's layout."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console

from py_checks.config import find_root
from py_checks.core import EXIT_OK, EXIT_VIOLATION
from py_checks.sync import stale, write

if TYPE_CHECKING:
    from collections.abc import Sequence


def sync(  # check-ok: keyword-only-arguments: typer parses the command's signature
    check: Annotated[
        bool,
        typer.Option("--check", help="write nothing, only say what is stale"),
    ] = False,
) -> None:
    """Build the files derived from the code: the import contracts and `.env.example`."""
    root = find_root(start=Path.cwd())
    console = Console(
        stderr=True,
        soft_wrap=True,
    )
    if check:
        raise typer.Exit(
            _report(
                stale=stale(root=root),
                console=console,
            )
        )
    for path in write(root=root):
        _say(
            text=f"built {path.relative_to(root)}",
            console=console,
        )
    raise typer.Exit(EXIT_OK)


def _report(
    *,
    stale: Sequence[Path],
    console: Console,
) -> int:
    """A built file has fallen behind what the settings declare or what is on disk."""
    for path in stale:
        _say(
            text=f"{path}: stale, run `py-checks sync`",
            console=console,
        )
    if stale:
        return EXIT_VIOLATION
    _say(
        text="ok: the built files match the code and the settings",
        console=console,
    )
    return EXIT_OK


def _say(
    *,
    text: str,
    console: Console,
) -> None:
    """Print as is: a line may hold paths and sections, markup has no place here."""
    console.print(
        text,
        markup=False,
        highlight=False,
    )


def register(*, app: typer.Typer) -> None:
    app.command("sync")(sync)
