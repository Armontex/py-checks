"""Which files need a translation, and which translation belongs to which file."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Final

from pathspec import GitIgnoreSpec

from py_checks.translations._constants import HOME
from py_checks.translations._errors import TranslationError

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

SEPARATOR: Final = "/"

# Tracked files and new ones git has not been told to ignore: a document just
# written is judged before `git add`, and `.venv/` is never a candidate.
LISTED: Final = ("git", "ls-files", "--cached", "--others", "--exclude-standard", "-z")


def tracked(*, root: Path) -> list[str]:
    """The repository's files, as paths from its root, that exist on disk.

    A file deleted but not yet staged is still listed by git; it has nothing
    to translate. A symlink is not a document of its own — `CLAUDE.md` pointing
    at `AGENTS.md` is translated once, as `AGENTS.md`.
    """
    try:
        finished = subprocess.run(  # noqa: S603 — a fixed list of arguments, no shell
            LISTED,
            cwd=root,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        message = f"{root} is not a git repository: translations are matched against its files"
        raise TranslationError(message) from error
    listed = finished.stdout.decode().split("\0")
    return sorted(
        path
        for path in listed
        if path and (root / path).is_file() and not (root / path).is_symlink()
    )


def selected(
    *,
    paths: Iterable[str],
    files: Iterable[str],
) -> list[str]:
    """The sources: the files the patterns select, never a translation itself."""
    spec = GitIgnoreSpec.from_lines(files)
    return [path for path in paths if not _translated(path=path) and spec.match_file(path)]


def dead(
    *,
    paths: Iterable[str],
    files: tuple[str, ...],
) -> list[str]:
    """The patterns that change nothing: without one, the same files are selected.

    One question covers both mistakes — a pattern that selects nothing, and a
    `!` that excludes nothing, like `!.github/` under a `*.md`.
    """
    candidates = list(paths)
    whole = selected(
        paths=candidates,
        files=files,
    )
    return [
        pattern
        for index, pattern in enumerate(files)
        if selected(
            paths=candidates,
            files=files[:index] + files[index + 1 :],
        )
        == whole
    ]


def translation_of(
    *,
    source: str,
    lang: str,
) -> str:
    return f"{HOME}/{lang}/{source}"


def source_of(*, translation: str) -> tuple[str, str] | None:
    """The language and the source of a translation; `None` — not one."""
    if not _translated(path=translation):
        return None
    lang, _, source = translation.removeprefix(f"{HOME}/").partition(SEPARATOR)
    if not lang or not source:
        return None
    return lang, source


def _translated(*, path: str) -> bool:
    return path.startswith(f"{HOME}/")
