"""Где в проекте лежат слои.

Контракт с несуществующим модулем валит весь прогон import-linter, поэтому
генератор сначала смотрит, что на диске есть. Подстановка (`pkg.modules.*.domain`)
ничего не ломает, когда не находит ничего, — её можно писать всегда.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_checks.contracts._constants import MIGRATIONS, MODULES, VERSIONS

if TYPE_CHECKING:
    from pathlib import Path


def package(*, root: Path, src: Path) -> str | None:
    """Корневой пакет проекта: единственный пакет внутри `src`."""
    source = root / src
    if not source.is_dir():
        return None
    found = [
        directory.name
        for directory in sorted(source.iterdir())
        if directory.is_dir() and (directory / "__init__.py").is_file()
    ]
    if len(found) != 1:
        return None
    return found[0]


def expressions(*, root: Path, src: Path, package: str, layer: str) -> tuple[str, ...]:
    """Как назвать слой в контракте: сам по себе, внутри модулей, или никак."""
    found: list[str] = []
    if (root / src / package / layer).is_dir():
        found.append(f"{package}.{layer}")
    if (root / src / package / MODULES).is_dir():
        found.append(f"{package}.{MODULES}.*.{layer}")
    return tuple(found)


def modules(*, root: Path, src: Path, package: str) -> bool:
    return (root / src / package / MODULES).is_dir()


def migrations(*, root: Path) -> bool:
    return (root / MIGRATIONS / VERSIONS).is_dir()
