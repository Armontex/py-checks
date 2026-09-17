"""Чтение `[tool.python-checks]` из `pyproject.toml` проекта."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from python_checks.config._config import Config
from python_checks.config._constants import SECTION
from python_checks.config._errors import ConfigError

if TYPE_CHECKING:
    from pathlib import Path


def find_root(start: Path) -> Path:
    """Ближайшая папка вверх по дереву, где лежит `pyproject.toml`.

    Именно она считается корнем проекта: пути в конфиге и в выводе даются
    относительно неё, чтобы строка нарушения не зависела от того, откуда
    запустили проверку.
    """
    for directory in (start, *start.parents):
        if (directory / "pyproject.toml").is_file():
            return directory
    return start


def load(root: Path) -> Config:
    """Настройки проекта; если секции нет — значения по умолчанию."""
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return Config()
    try:
        document = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"{pyproject}: {error}") from error
    section = document.get("tool", {}).get(SECTION, {})
    return _build(section, source=pyproject)


def _build(section: dict[str, Any], *, source: Path) -> Config:
    own, checks = _split(section)
    try:
        return Config.model_validate({**own, "checks": checks})
    except ValidationError as error:
        raise ConfigError(f"{source} [tool.{SECTION}]: {error}") from error


def _split(section: dict[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Свои ключи отдельно, вложенные таблицы проверок отдельно."""
    own: dict[str, Any] = {}
    checks: dict[str, dict[str, Any]] = {}
    for key, value in section.items():
        if isinstance(value, dict):
            checks[key] = value  # pyright: ignore[reportUnknownArgumentType]
        else:
            own[key] = value
    return own, checks
