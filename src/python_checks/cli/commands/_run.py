"""Команда `run`: прогнать проверки."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from python_checks.config import Config, find_root, load
from python_checks.core import (
    FileCheck,
    Violation,
    available,
    fix,
    get,
    inspect,
    python_files,
    reformat,
    report,
)


def run(  # check-ok: keyword-only-arguments: подпись команды разбирает typer
    paths: Annotated[
        list[Path] | None,
        typer.Argument(help="файлы или папки; без них — весь `src` проекта"),
    ] = None,
    select: Annotated[
        list[str] | None,
        typer.Option("--select", "-s", help="коды проверок; без них — все включённые"),
    ] = None,
    autofix: Annotated[
        bool,
        typer.Option("--fix", help="исправить то, что правится само"),
    ] = False,
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
    violations = inspect(files=files, checks=checks, config=config, root=root)
    if autofix:
        violations = _fixed(violations=violations)
    raise typer.Exit(report(violations=violations, root=root, checked=len(files)))


def _fixed(*, violations: list[Violation]) -> list[Violation]:
    """Наложить правки и вернуть то, что осталось человеку."""
    changed, left = fix(violations=violations)
    reformat(paths=changed)
    return left


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
