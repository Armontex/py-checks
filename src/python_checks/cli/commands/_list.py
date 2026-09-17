"""Команда `list`: какие проверки есть."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table

from python_checks.cli.commands._summary import summary
from python_checks.config import find_root, load
from python_checks.core import available


def list_checks() -> None:
    """Показать все проверки: код, состояние и одну строку описания."""
    config = load(find_root(Path.cwd()))
    table = Table(box=None, pad_edge=False)
    table.add_column("код")
    table.add_column("состояние")
    table.add_column("что делает")
    for code, check in sorted(available().items()):
        state = "вкл" if config.enabled(code) else "выкл"
        table.add_row(code, state, summary(check))
    Console().print(table)
