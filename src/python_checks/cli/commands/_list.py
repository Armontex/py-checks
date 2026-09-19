"""Команда `list`: какие проверки есть."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

from python_checks.cli.commands._summary import summary
from python_checks.config import find_root, load
from python_checks.core import available, available_project

if TYPE_CHECKING:
    import typer


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
    listed = {**available(), **available_project()}
    for code, check in sorted(listed.items()):
        state = "вкл" if config.enabled(code=code) else "выкл"
        table.add_row(code, state, summary(check=check))
    Console().print(table)


def register(*, app: typer.Typer) -> None:
    app.command("list")(list_checks)
