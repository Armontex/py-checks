"""Чтение `[tool.python-checks]` из `pyproject.toml` проекта."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

from pydantic import ValidationError

from python_checks.config._config import Config
from python_checks.config._constants import PYPROJECT, SECTION
from python_checks.config._errors import ConfigError

if TYPE_CHECKING:
    from pathlib import Path

    from python_checks.config._toml import TomlTable, TomlValue


def find_root(*, start: Path) -> Path:
    """Ближайшая папка вверх по дереву, где лежит `pyproject.toml`.

    Именно она считается корнем проекта: пути в конфиге и в выводе даются
    относительно неё, чтобы строка нарушения не зависела от того, откуда
    запустили проверку.
    """
    for directory in (start, *start.parents):
        if (directory / PYPROJECT).is_file():
            return directory
    return start


def load(*, root: Path) -> Config:
    """Настройки проекта; если секции нет — значения по умолчанию."""
    pyproject = root / PYPROJECT
    if not pyproject.is_file():
        return Config()
    try:
        document: TomlTable = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"{pyproject}: {error}") from error
    return _build(
        section=_section(document=document),
        source=pyproject,
    )


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
    try:
        return Config.model_validate({**own, "checks": checks})
    except ValidationError as error:
        raise ConfigError(f"{source} [tool.{SECTION}]: {error}") from error


def _split(*, section: TomlTable) -> tuple[TomlTable, dict[str, TomlTable]]:
    """Свои ключи отдельно, вложенные таблицы проверок отдельно."""
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
