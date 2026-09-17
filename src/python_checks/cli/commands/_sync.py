"""Команда `sync`: разложить эталонные конфиги по проекту."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console

from python_checks.config import PYPROJECT, find_root
from python_checks.core import EXIT_OK, EXIT_VIOLATION
from python_checks.sync import DIRECTORY, leftovers, stale, write

if TYPE_CHECKING:
    from collections.abc import Sequence


def sync(  # check-ok: keyword-only-arguments: подпись команды разбирает typer
    check: Annotated[
        bool,
        typer.Option("--check", help="ничего не писать, только сказать, что разошлось"),
    ] = False,
) -> None:
    """Положить общие настройки ruff и pyright в `.python-checks/` проекта."""
    root = find_root(start=Path.cwd())
    console = Console(stderr=True, soft_wrap=True)
    forgotten = leftovers(root=root)
    if check:
        raise typer.Exit(_report(stale=stale(root=root), forgotten=forgotten, console=console))
    for path in write(root=root):
        _say(text=f"записан {path.relative_to(root)}", console=console)
    _forgotten(paths=forgotten, console=console)
    raise typer.Exit(EXIT_OK)


def _report(*, stale: Sequence[Path], forgotten: Sequence[str], console: Console) -> int:
    for path in stale:
        _say(
            text=f"{path}: разошёлся с библиотекой, запусти `python-checks sync`",
            console=console,
        )
    _forgotten(paths=forgotten, console=console)
    if stale or forgotten:
        return EXIT_VIOLATION
    _say(text=f"ok: {DIRECTORY} совпадает с библиотекой", console=console)
    return EXIT_OK


def _forgotten(*, paths: Sequence[str], console: Console) -> None:
    for section in paths:
        _say(
            text=(
                f"{PYPROJECT}: секцию [{section}] инструмент больше не читает — "
                "он нашёл свой файл в корне; перенеси её туда"
            ),
            console=console,
        )


def _say(*, text: str, console: Console) -> None:
    """Печатать как есть: в строке бывают `[tool.ruff]` и пути, разметка тут лишняя."""
    console.print(text, markup=False, highlight=False)


def register(*, app: typer.Typer) -> None:
    app.command("sync")(sync)
