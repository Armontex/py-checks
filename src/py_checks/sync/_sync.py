"""Конфиги, которые собирает библиотека."""

from __future__ import annotations

from typing import TYPE_CHECKING

from py_checks.config import load
from py_checks.contracts import FILE, render
from py_checks.environment import render as environment

if TYPE_CHECKING:
    from pathlib import Path


def planned(*, root: Path) -> dict[Path, str]:
    """Что библиотека собирает для этого проекта.

    Настройки ruff, pyright и прочих инструментов сюда не входят: их приносит
    шаблон, и дальше это файлы проекта. Собирается то, что обязано совпадать с
    кодом и расходится молча: контракты импортов — с раскладкой на диске (слой,
    которого нет, роняет весь прогон import-linter), `.env.example` — с полями
    классов настроек (переменная, которой нет в файле, обнаруживается на проде).
    """
    config = load(root=root)
    built: dict[Path, str] = {}
    contracts = render(
        root=root,
        config=config,
    )
    if contracts is not None:
        built[root / FILE] = contracts
    variables = environment(
        root=root,
        config=config,
    )
    if variables is not None:
        path, text = variables
        built[path] = text
    return built


def stale(*, root: Path) -> list[Path]:
    """Файлы, которые разошлись с тем, что собралось бы сейчас."""
    return [path for path, text in planned(root=root).items() if _read(path=path) != text]


def write(*, root: Path) -> list[Path]:
    """Собрать заново; вернуть то, что изменилось."""
    changed: list[Path] = []
    for path, text in planned(root=root).items():
        if _read(path=path) != text:
            path.write_text(text, encoding="utf-8")
            changed.append(path)
    return changed


def _read(*, path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")
