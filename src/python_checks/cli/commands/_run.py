"""Команда `run`: прогнать проверки."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

from python_checks.config import Config, find_root, load
from python_checks.core import (
    Checks,
    Scope,
    Violation,
    available,
    fix,
    get,
    python_files,
    reformat,
    report,
    survey,
)

if TYPE_CHECKING:
    from python_checks.core import Check


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
    everything: Annotated[
        bool,
        typer.Option("--all", help="вместе с правилами, которым нужна живая среда"),
    ] = False,
) -> None:
    """Проверить файлы и вернуть код выхода: 0 — чисто, 1 — есть нарушения."""
    root = find_root(start=Path.cwd())
    config = load(root=root)
    chosen = _chosen(
        select=select,
        config=config,
        paths=bool(paths),
        everything=everything,
    )
    # Обход дерева нужен только файловым правилам: прогон одного правила про
    # проект не должен читать список из тысячи файлов, чтобы никому его не дать.
    files = (
        python_files(
            paths=paths or [],
            root=root,
            default=root / config.src,
            exclude=config.excluded,
        )
        if chosen.files
        else []
    )
    violations = survey(
        chosen=chosen,
        files=files,
        config=config,
        root=root,
    )
    if autofix:
        violations = _fixed(violations=violations)
    raise typer.Exit(
        report(
            violations=violations,
            root=root,
            checked=len(files),
        )
    )


def _fixed(*, violations: list[Violation]) -> list[Violation]:
    """Наложить правки и вернуть то, что осталось человеку."""
    changed, left = fix(violations=violations)
    reformat(paths=changed)
    return left


def _chosen(
    *,
    select: list[str] | None,
    config: Config,
    paths: bool,
    everything: bool,
) -> Checks:
    """Выбранные проверки, а без выбора — все, кроме отключённых в конфиге.

    Явный `--select` сильнее всего остального: если проверку позвали по имени,
    значит её хотят запустить именно сейчас — и несмотря на `ignore`, и
    несмотря на то, что ей нужна база.
    """
    listed = available()
    if select:
        return listed.only(codes={get(code=code).code for code in select})
    return listed.only(
        codes={
            code
            for code, check in listed.listed.items()
            if config.enabled(code=code)
            and _wanted(
                check=check,
                paths=paths,
                everything=everything,
            )
        }
    )


def _wanted(
    *,
    check: Check,
    paths: bool,
    everything: bool,
) -> bool:
    """Входит ли правило в прогон, которому не назвали имён.

    Названные пути правил про проект не касаются: прогон по одному файлу
    проверяет этот файл, а не проект вокруг него. Правилу, которому нужна
    живая среда, место в CI, а не в хуке на коммит, — его зовут `--all` или по
    имени.
    """
    if paths and check.scope is not Scope.FILE:
        return False
    if check.scope is Scope.ENVIRONMENT:
        return everything
    return True


def register(*, app: typer.Typer) -> None:
    app.command("run")(run)
