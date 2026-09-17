"""Общие настройки проекта."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, ValidationError

from python_checks.config._base import CheckSettings
from python_checks.config._constants import DEFAULT_EXCLUDE, SECTION
from python_checks.config._errors import ConfigError
from python_checks.config._toml import TomlTable


class Config(CheckSettings):
    """Где искать код и что не проверять.

    Настройки самих проверок сюда не попадают: они лежат в своих секциях и
    разбираются моделью той проверки, которой принадлежат. Ядро держит их
    нетронутыми в `checks` и отдаёт владельцу через `settings_for`.
    """

    src: Path = Path("src")
    exclude: tuple[str, ...] = DEFAULT_EXCLUDE
    ignore: tuple[str, ...] = ()
    checks: dict[str, TomlTable] = Field(default_factory=dict, exclude=True)

    def section(self, code: str) -> TomlTable:
        return self.checks.get(code, {})

    def settings_for(self, code: str, model: type[CheckSettings]) -> CheckSettings:
        """Настройки проверки: её секция, проверенная её же моделью."""
        try:
            return model.model_validate(self.section(code))
        except ValidationError as error:
            raise ConfigError(f"[tool.{SECTION}.{code}]: {error}") from error

    def enabled(self, code: str) -> bool:
        return code not in self.ignore
