"""Чтение `[tool.python-checks]` из `pyproject.toml` проекта."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from pydantic import Field, ValidationError

from python_checks.config._base import CheckSettings

SECTION = "python-checks"

DEFAULT_EXCLUDE: tuple[str, ...] = (
    ".venv/*",
    "build/*",
    "dist/*",
    "**/__pycache__/*",
    "**/migrations/versions/*",
)


class ConfigError(Exception):
    """Конфиг есть, но прочитать его нельзя."""


class Config(CheckSettings):
    """Общие настройки: где искать код и что не проверять.

    Настройки самих проверок сюда не попадают: они лежат в своих секциях и
    разбираются моделью той проверки, которой принадлежат.
    """

    src: Path = Path("src")
    exclude: tuple[str, ...] = DEFAULT_EXCLUDE
    ignore: tuple[str, ...] = ()
    checks: dict[str, dict[str, Any]] = Field(default_factory=dict, exclude=True)

    def section(self, code: str) -> dict[str, Any]:
        return self.checks.get(code, {})

    def settings_for(self, code: str, model: type[CheckSettings]) -> CheckSettings:
        """Настройки проверки: её секция, проверенная её же моделью."""
        try:
            return model.model_validate(self.section(code))
        except ValidationError as error:
            raise ConfigError(f"[tool.{SECTION}.{code}]: {error}") from error

    def enabled(self, code: str) -> bool:
        return code not in self.ignore


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
    return _parse(document.get("tool", {}).get(SECTION, {}), source=pyproject)


def _parse(section: dict[str, Any], *, source: Path) -> Config:
    own: dict[str, Any] = {}
    checks: dict[str, dict[str, Any]] = {}
    for key, value in section.items():
        if isinstance(value, dict):
            checks[key] = value  # pyright: ignore[reportUnknownArgumentType]
        else:
            own[key] = value
    try:
        return Config.model_validate({**own, "checks": checks})
    except ValidationError as error:
        raise ConfigError(f"{source} [tool.{SECTION}]: {error}") from error
