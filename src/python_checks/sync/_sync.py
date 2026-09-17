"""Копии эталонов в проекте: что разошлось и что записать."""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_checks.config import load
from python_checks.contracts import FILE, render
from python_checks.sync._canonical import canonical
from python_checks.sync._constants import DIRECTORY
from python_checks.sync._managed import MANAGED

if TYPE_CHECKING:
    from pathlib import Path


def planned(*, root: Path) -> dict[Path, str]:
    """Что должно лежать в `.python-checks` этого проекта.

    Часть файлов у всех одинаковая и просто копируется, часть собирается под
    раскладку: контракты импортов знают имя пакета и то, каких слоёв в проекте
    нет. Для сверки разницы между ними нет — сравнивается текст.
    """
    files = {root / DIRECTORY / managed.name: canonical(name=managed.name) for managed in MANAGED}
    contracts = render(root=root, config=load(root=root))
    if contracts is not None:
        files[root / DIRECTORY / FILE] = contracts
    return files


def stale(*, root: Path) -> list[Path]:
    """Файлы, которые разошлись с библиотекой или которых нет.

    Разойтись они могут двумя способами: кто-то поправил копию руками или
    обновилась библиотека. Оба случая — одна и та же работа, `sync`.
    """
    return [path for path, text in planned(root=root).items() if _read(path=path) != text]


def write(*, root: Path) -> list[Path]:
    """Разложить эталоны по проекту; вернуть то, что изменилось."""
    changed: list[Path] = []
    (root / DIRECTORY).mkdir(exist_ok=True)
    for path, text in planned(root=root).items():
        if _read(path=path) != text:
            path.write_text(text, encoding="utf-8")
            changed.append(path)
    for managed in MANAGED:
        project = root / managed.project
        if not project.exists():
            project.write_text(managed.stub, encoding="utf-8")
            changed.append(project)
    return changed


def _read(*, path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")
