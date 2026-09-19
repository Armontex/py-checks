"""Конфиги, которые собирает библиотека."""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_checks.config import load
from python_checks.contracts import FILE, render

if TYPE_CHECKING:
    from pathlib import Path


def planned(*, root: Path) -> dict[Path, str]:
    """Что библиотека собирает для этого проекта.

    Настройки ruff, pyright и прочих инструментов сюда не входят: их приносит
    шаблон, и дальше это файлы проекта. Контракты импортов — другое дело: они
    обязаны соответствовать тому, что лежит на диске сегодня, а статический
    файл начнёт врать, как только появится новый слой, и import-linter упадёт
    на первом же несуществующем модуле.
    """
    contracts = render(
        root=root,
        config=load(root=root),
    )
    if contracts is None:
        return {}
    return {root / FILE: contracts}


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
