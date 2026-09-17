"""Копии эталонов в проекте: что разошлось и что записать."""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_checks.sync._canonical import canonical
from python_checks.sync._constants import DIRECTORY
from python_checks.sync._managed import MANAGED

if TYPE_CHECKING:
    from pathlib import Path


def stale(*, root: Path) -> list[Path]:
    """Копии, которые разошлись с библиотекой или которых нет.

    Разойтись они могут двумя способами: кто-то поправил копию руками или
    обновилась библиотека. Оба случая — одна и та же работа, `sync`.
    """
    found: list[Path] = []
    for managed in MANAGED:
        path = root / DIRECTORY / managed.name
        if _read(path=path) != canonical(name=managed.name):
            found.append(path)
    return found


def write(*, root: Path) -> list[Path]:
    """Разложить эталоны по проекту; вернуть то, что изменилось."""
    changed: list[Path] = []
    (root / DIRECTORY).mkdir(exist_ok=True)
    for managed in MANAGED:
        copy = root / DIRECTORY / managed.name
        text = canonical(name=managed.name)
        if _read(path=copy) != text:
            copy.write_text(text, encoding="utf-8")
            changed.append(copy)
        project = root / managed.project
        if not project.exists():
            project.write_text(managed.stub, encoding="utf-8")
            changed.append(project)
    return changed


def _read(*, path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")
