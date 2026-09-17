"""Команда `run`: прогнать проверки."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from python_checks.config import Config, find_root, load
from python_checks.core import FileCheck, available, get, inspect, python_files, report


def run(  # check-ok: keyword-only-arguments: подпись команды разбирает typer
    paths: Annotated[
        list[Path] | None,
        typer.Argument(help="файлы или папки; без них — весь `src` проекта"),
    ] = None,
    select: Annotated[
        list[str] | None,
        typer.Option("--select", "-s", help="коды проверок; без них — все включённые"),
    ] = None,
) -> None:
    """Проверить файлы и вернуть код выхода: 0 — чисто, 1 — есть нарушения."""
    root = find_root(start=Path.cwd())
    config = load(root=root)
    checks = _chosen(select=select, config=config)
    files = python_files(
        paths=paths or [],
        root=root,
        default=root / config.src,
        exclude=config.excluded,
    )
    violations = inspect(files=files, checks=checks, config=config)
    raise typer.Exit(report(violations=violations, root=root, checked=len(files)))


def _chosen(*, select: list[str] | None, config: Config) -> list[FileCheck]:
    """Выбранные проверки, а без выбора — все, кроме отключённых в конфиге.

    Явный `--select` сильнее `ignore`: если проверку позвали по имени, значит её
    хотят запустить именно сейчас.
    """
    if select:
        return [get(code=code) for code in select]
    return [check for code, check in sorted(available().items()) if config.enabled(code=code)]


def register(*, app: typer.Typer) -> None:
    app.command("run")(run)
