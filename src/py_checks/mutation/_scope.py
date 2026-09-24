"""Что mutmut мутирует и как он называет мутантов."""

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

# `pushed` pre-commit отдаёт хуку на пуш как то, что пуш заменяет; у новой
# ветки это строка из нулей.
PUSHED: Final = "PRE_COMMIT_FROM_REF"
NO_SUCH_REF: Final = "0" * 40


@dataclass(frozen=True, slots=True)
class Scope:
    """Где mutmut ищет код и как из пути выходит имя его мутанта."""

    sources: tuple[PurePosixPath, ...]
    spared: tuple[str, ...]
    src: PurePosixPath

    def module_of(self, *, path: PurePosixPath) -> str | None:
        """Модуль, под которым файл мутируется, или ничего, если не мутируется.

        mutmut называет мутанта путём импорта: от корня, откуда импортируют, —
        `src` у раскладки с ним и корень проекта у плоской. У пакета `__init__`
        он отбрасывает, прежде чем записать имя.
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
    """Область мутаций, прочитанная так же, как её читает mutmut.

    `[tool.mutmut]` в `pyproject.toml` побеждает, если он есть; иначе
    `[mutmut]` в `setup.cfg`. Ни там ни там — отказ: гейт, не знающий, что
    мутируется, судил бы пустоту и молча пропускал бы всё.
    """
    declared = _pyproject(root=root) or _setup(root=root)
    sources = declared.get(SOURCES, ())
    if not sources:
        raise GateError(
            f"mutmut не знает, что мутировать: нет `{SOURCES}` "
            f"ни в [tool.{TOOL}] {PYPROJECT}, ни в [{TOOL}] {SETUP}"
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
    """Мутируемые модули, которые тронула ветка, — одним вызовом git.

    `A...B` — это общий предок: ветку судят по её собственным правкам, а не
    по всему, что develop принял с тех пор, как она от него ушла.
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
    """С чем сравнивать: с тем, что пуш заменяет, иначе с первым известным.

    pre-commit отдаёт хуку на пуш текущий sha удалённой ветки — ровно то,
    что нужно, — а у новой ветки это нули. Тогда develop, под тем именем,
    которое знает этот клон.
    """
    pushed = os.environ.get(PUSHED, "")
    if pushed and pushed != NO_SUCH_REF:
        return pushed
    for candidate in candidates:
        known = shell.finished(command=("git", "rev-parse", "--verify", "--quiet", candidate))
        if not known.returncode:
            return candidate
    return None
