"""Which files are checked."""

from __future__ import annotations

from fnmatch import fnmatch
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path


def python_files(
    *,
    paths: Sequence[Path],
    root: Path,
    default: Path,
    exclude: Iterable[str] = (),
) -> list[Path]:
    """Every `.py` under the given paths, minus the excluded ones.

    pre-commit passes the list of changed files, so a path may be a file or a
    directory. When there are no paths — a run by hand — `default` is taken
    (usually `src`), not the whole repository: otherwise `.venv` and other
    code that is not ours would be picked up.
    """
    roots = list(paths) if paths else [default]
    patterns = tuple(exclude)
    found: set[Path] = set()
    for entry in roots:
        found.update(_walk(entry=entry))
    return sorted(
        path
        for path in found
        if not _excluded(
            path=path,
            root=root,
            patterns=patterns,
        )
    )


def _walk(*, entry: Path) -> Iterable[Path]:
    if entry.is_dir():
        return entry.rglob("*.py")
    return [entry] if entry.suffix == ".py" else []


def _excluded(
    *,
    path: Path,
    root: Path,
    patterns: tuple[str, ...],
) -> bool:
    relative = path.relative_to(root) if path.is_relative_to(root) else path
    as_posix = relative.as_posix()
    return any(fnmatch(as_posix, pattern) for pattern in patterns)
