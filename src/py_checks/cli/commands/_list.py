"""Команда `list`: какие проверки есть."""

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
    """Показать все проверки: код, состояние и одну строку описания."""
    config = load(root=find_root(start=Path.cwd()))
    table = Table(
        box=None,
        pad_edge=False,
    )
    table.add_column("код")
    table.add_column("состояние")
    table.add_column("что делает")
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
    """Включено, выключено — или включено, но не в обычном прогоне.

    Правилу, которому нужна живая среда, место в CI, поэтому вместо «вкл» в
    таблице стоит то, чем его зовут.
    """
    if not config.enabled(code=check.code):
        return "выкл"
    if check.scope is Scope.ENVIRONMENT:
        return "--all"
    return "вкл"


def register(*, app: typer.Typer) -> None:
    app.command("list")(list_checks)
