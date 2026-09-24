"""The configs the library builds."""

from __future__ import annotations

from typing import TYPE_CHECKING

from py_checks.config import load
from py_checks.contracts import FILE, render
from py_checks.environment import render as environment

if TYPE_CHECKING:
    from pathlib import Path


def planned(*, root: Path) -> dict[Path, str]:
    """What the library builds for this project.

    The settings of ruff, pyright and other tools are not part of it: the
    template brings them, and from then on they are the project's files. What
    is built is what has to match the code and drifts silently: the import
    contracts — with the layout on disk (a missing layer brings down the whole
    import-linter run), `.env.example` — with the fields of the settings
    classes (a variable missing from the file is discovered in production).
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
    """Files that have drifted from what would be built now."""
    return [path for path, text in planned(root=root).items() if _read(path=path) != text]


def write(*, root: Path) -> list[Path]:
    """Build again; return what changed."""
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
