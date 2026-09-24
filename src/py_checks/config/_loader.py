"""Reading the settings: from the project's own file or from `pyproject.toml`."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING, Final

from pydantic import ValidationError

from py_checks.config._config import Config, prefix, retired
from py_checks.config._constants import PYPROJECT, SECTION, STANDALONE
from py_checks.config._errors import ConfigError

if TYPE_CHECKING:
    from pathlib import Path

    from py_checks.config._toml import TomlTable, TomlValue

# Every file that marks the project root. `pyproject.toml` comes last: a
# project nearly always has one, and its own settings file sits next to it.
ANCHORS: Final[tuple[str, ...]] = (*STANDALONE, PYPROJECT)


def find_root(*, start: Path) -> Path:
    """The nearest folder up the tree that holds the manifest or the own settings file.

    That folder is taken as the project root: paths in the config and in the
    output are relative to it, so a violation line does not depend on where
    the check was run from.
    """
    for directory in (start, *start.parents):
        if any((directory / name).is_file() for name in ANCHORS):
            return directory
    return start


def load(*, root: Path) -> Config:
    """The project's settings; if there are none anywhere, the defaults.

    The settings live either in the tool's own file — `py-checks.toml` or
    `pychecks.toml`, with or without a leading dot — or as the
    `[tool.py-checks]` section in `pyproject.toml`. The tool's own file
    has no prefix: the whole file is that section.

    Two places at once are not allowed: that is not a merge but a question
    with no answer, and it is better to ask it out loud than to read one
    silently and forget the other.
    """
    found = _found(root=root)
    if not found:
        return Config()
    if len(found) > 1:
        raise ConfigError(
            "the settings are in more than one place: "
            + ", ".join(source.name for source, _ in found)
            + "; keep one, otherwise nobody knows which of them is read"
        )
    source, section = found[0]
    return _build(
        section=section,
        source=source,
    )


def _found(*, root: Path) -> list[tuple[Path, TomlTable]]:
    """The files that actually hold this tool's settings.

    A `pyproject.toml` without the section does not count as a settings file:
    every project has one, and being there silently is not the author's choice.
    """
    found: list[tuple[Path, TomlTable]] = []
    for name in STANDALONE:
        path = root / name
        if path.is_file():
            found.append((path, _document(path=path)))
    pyproject = root / PYPROJECT
    if pyproject.is_file() and (section := _section(document=_document(path=pyproject))):
        found.append((pyproject, section))
    return found


def _document(*, path: Path) -> TomlTable:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"{path}: {error}") from error


def _section(*, document: TomlTable) -> TomlTable:
    tool = document.get("tool")
    section = tool.get(SECTION) if isinstance(tool, dict) else None
    return section if isinstance(section, dict) else {}


def _build(
    *,
    section: TomlTable,
    source: Path,
) -> Config:
    own, checks = _split(section=section)
    retired(
        checks=checks,
        source=source,
    )
    named = prefix(source=source)
    # The tool's own file has no section — there is nothing to name in the message but the file.
    where = f" [{named.rstrip('.')}]" if named else ""
    try:
        return Config.model_validate({**own, "checks": checks, "origin": source})
    except ValidationError as error:
        raise ConfigError(f"{source}{where}: {error}") from error


def _split(*, section: TomlTable) -> tuple[TomlTable, dict[str, TomlTable]]:
    """The top-level keys on one side, the nested check tables on the other."""
    own: TomlTable = {}
    checks: dict[str, TomlTable] = {}
    for key, value in section.items():
        _place(
            key=key,
            value=value,
            own=own,
            checks=checks,
        )
    return own, checks


def _place(
    *,
    key: str,
    value: TomlValue,
    own: TomlTable,
    checks: dict[str, TomlTable],
) -> None:
    if isinstance(value, dict):
        checks[key] = value
    else:
        own[key] = value
