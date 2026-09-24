"""The `list` command: which checks exist."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

from py_checks.cli.commands._summary import summary
from py_checks.config import find_root, load
from py_checks.core import Scope, available

if TYPE_CHECKING:
    import typer

    from py_checks.config import Config
    from py_checks.core import Check


def list_checks() -> None:
    """Show every check: its code, its state and one line of description."""
    config = load(root=find_root(start=Path.cwd()))
    table = Table(
        box=None,
        pad_edge=False,
    )
    table.add_column("code")
    table.add_column("state")
    table.add_column("what it does")
    for code, check in sorted(available().listed.items()):
        table.add_row(
            code,
            _state(
                check=check,
                config=config,
            ),
            summary(check=check),
        )
    Console().print(table)


def _state(
    *,
    check: Check,
    config: Config,
) -> str:
    """On, off — or on, but not in an ordinary run.

    A rule that needs a live environment belongs in CI, so instead of "on" the
    table shows what calls it.
    """
    if not config.enabled(code=check.code):
        return "off"
    if check.scope is Scope.ENVIRONMENT:
        return "--all"
    return "on"


def register(*, app: typer.Typer) -> None:
    app.command("list")(list_checks)
