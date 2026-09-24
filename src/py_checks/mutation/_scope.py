"""What mutmut mutates and how it names mutants."""

from __future__ import annotations

import os
import tomllib
from configparser import ConfigParser
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Final

from py_checks.config import PYPROJECT
from py_checks.mutation._errors import GateError

if TYPE_CHECKING:
    from pathlib import Path

    from py_checks.config import TomlTable
    from py_checks.mutation._process import Shell

SOURCES: Final = "source_paths"
SPARED: Final = "do_not_mutate"
SETUP: Final = "setup.cfg"
TOOL: Final = "mutmut"
SUFFIX: Final = ".py"
PACKAGE: Final = "__init__"

# pre-commit hands the push hook `pushed` as what the push replaces; for a new
# branch it is a string of zeros.
PUSHED: Final = "PRE_COMMIT_FROM_REF"
NO_SUCH_REF: Final = "0" * 40


@dataclass(frozen=True, slots=True)
class Scope:
    """Where mutmut looks for code and how a path becomes its mutant's name."""

    sources: tuple[PurePosixPath, ...]
    spared: tuple[str, ...]
    src: PurePosixPath

    def module_of(self, *, path: PurePosixPath) -> str | None:
        """The module the file is mutated under, or nothing if it is not mutated.

        mutmut names a mutant by its import path: from the root it is imported
        from — `src` in a layout that has one, the project root in a flat one.
        For a package it drops `__init__` before writing the name down.
        """
        inside = any(path.is_relative_to(source) for source in self.sources)
        spared = any(fnmatch(path.as_posix(), pattern) for pattern in self.spared)
        if not inside or spared or path.suffix != SUFFIX or not path.is_relative_to(self.src):
            return None
        parts = path.relative_to(self.src).with_suffix("").parts
        named = parts[:-1] if parts[-1] == PACKAGE else parts
        return ".".join(named) or None


def scope(
    *,
    root: Path,
    src: Path,
) -> Scope:
    """The mutation scope, read the same way mutmut reads it.

    `[tool.mutmut]` in `pyproject.toml` wins if there is one; otherwise
    `[mutmut]` in `setup.cfg`. Neither — a refusal: a gate that does not know
    what is mutated would judge nothing and silently pass everything.
    """
    declared = _pyproject(root=root) or _setup(root=root)
    sources = declared.get(SOURCES, ())
    if not sources:
        raise GateError(
            f"mutmut does not know what to mutate: set `{SOURCES}` "
            f"in [tool.{TOOL}] of {PYPROJECT} or in [{TOOL}] of {SETUP}"
        )
    return Scope(
        sources=tuple(PurePosixPath(one) for one in sources),
        spared=declared.get(SPARED, ()),
        src=PurePosixPath(src.as_posix()),
    )


def _pyproject(*, root: Path) -> dict[str, tuple[str, ...]]:
    path = root / PYPROJECT
    if not path.is_file():
        return {}
    document: TomlTable = tomllib.loads(path.read_text(encoding="utf-8"))
    tool = document.get("tool")
    table = tool.get(TOOL) if isinstance(tool, dict) else None
    if not isinstance(table, dict):
        return {}
    return {key: _strings(value=table.get(key)) for key in (SOURCES, SPARED)}


def _strings(*, value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        return tuple(one for one in value if isinstance(one, str))  # pyright: ignore[reportUnknownVariableType]
    return ()


def _setup(*, root: Path) -> dict[str, tuple[str, ...]]:
    parser = ConfigParser()
    parser.read(root / SETUP, encoding="utf-8")
    return {
        key: tuple(
            line.strip() for line in parser.get(TOOL, key, fallback="").splitlines() if line.strip()
        )
        for key in (SOURCES, SPARED)
    }


def changed(
    *,
    shell: Shell,
    against: str,
    area: Scope,
) -> tuple[str, ...]:
    """The mutated modules the branch touched — in a single git call.

    `A...B` is the common ancestor: a branch is judged by its own changes, not
    by everything develop has taken in since the branch left it.
    """
    listed = shell.answered(
        command=("git", "diff", "--name-only", "--diff-filter=d", f"{against}...HEAD"),
    )
    modules = {
        module
        for line in listed.splitlines()
        if (module := area.module_of(path=PurePosixPath(line.strip()))) is not None
    }
    return tuple(sorted(modules))


def against_ref(
    *,
    shell: Shell,
    candidates: tuple[str, ...],
) -> str | None:
    """What to compare against: what the push replaces, otherwise the first known.

    pre-commit hands the push hook the remote branch's current sha — exactly
    what is needed — and for a new branch it is zeros. Then develop, under
    whichever name this clone knows it by.
    """
    pushed = os.environ.get(PUSHED, "")
    if pushed and pushed != NO_SUCH_REF:
        return pushed
    for candidate in candidates:
        known = shell.finished(command=("git", "rev-parse", "--verify", "--quiet", candidate))
        if not known.returncode:
            return candidate
    return None
