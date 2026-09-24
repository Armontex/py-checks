"""Where the project's layers are.

A contract naming a module that does not exist fails the whole import-linter
run, so the generator first looks at what is on disk. A wildcard
(`pkg.modules.*.domain`) breaks nothing when it matches nothing — it can
always be written.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from py_checks.contracts._constants import MIGRATIONS, MODULES, VERSIONS

if TYPE_CHECKING:
    from pathlib import Path


def package(
    *,
    root: Path,
    src: Path,
) -> str | None:
    """The project's root package: the only package inside `src`."""
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


def expressions(
    *,
    root: Path,
    src: Path,
    package: str,
    layer: str,
) -> tuple[str, ...]:
    """How a contract names the layer: on its own, inside the modules, or not at all."""
    found: list[str] = []
    if (root / src / package / layer).is_dir():
        found.append(f"{package}.{layer}")
    if (root / src / package / MODULES).is_dir():
        found.append(f"{package}.{MODULES}.*.{layer}")
    return tuple(found)


def modules(
    *,
    root: Path,
    src: Path,
    package: str,
) -> bool:
    return (root / src / package / MODULES).is_dir()


def migrations(*, root: Path) -> bool:
    return (root / MIGRATIONS / VERSIONS).is_dir()
