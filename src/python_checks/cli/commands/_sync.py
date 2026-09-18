"""Команда `sync`: собрать конфиги, которые зависят от раскладки проекта."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console

from python_checks.config import find_root
from python_checks.core import EXIT_OK, EXIT_VIOLATION
from python_checks.sync import stale, write

if TYPE_CHECKING:
    from collections.abc import Sequence


def sync(  # check-ok: keyword-only-arguments: подпись команды разбирает typer
    check: Annotated[
        bool,
        typer.Option("--check", help="ничего не писать, только сказать, что устарело"),
    ] = False,
) -> None:
    """Собрать контракты импортов из слоёв, объявленных проектом."""
    root = find_root(start=Path.cwd())
    console = Console(stderr=True, soft_wrap=True)
    if check:
        raise typer.Exit(_report(stale=stale(root=root), console=console))
    for path in write(root=root):
        _say(text=f"собран {path.relative_to(root)}", console=console)
    raise typer.Exit(EXIT_OK)


def _report(*, stale: Sequence[Path], console: Console) -> int:
    """Собранный файл отстал от того, что объявлено в настройках или лежит на диске."""
    for path in stale:
        _say(text=f"{path}: устарел, запусти `python-checks sync`", console=console)
    if stale:
        return EXIT_VIOLATION
    _say(text="ok: контракты совпадают с настройками", console=console)
    return EXIT_OK


def _say(*, text: str, console: Console) -> None:
    """Печатать как есть: в строке бывают пути и секции, разметка тут лишняя."""
    console.print(text, markup=False, highlight=False)


def register(*, app: typer.Typer) -> None:
    app.command("sync")(sync)
