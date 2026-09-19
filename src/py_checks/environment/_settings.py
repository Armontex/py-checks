"""Классы настроек, из которых собирается пример окружения."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import ValidationError

from py_checks.config import CheckSettings, ConfigError, prefix
from py_checks.environment._constants import FILE, SECTION

if TYPE_CHECKING:
    from py_checks.config import Config


class Example(CheckSettings):
    """Секция `[tool.py-checks.env-example]`.

    `settings` — классы настроек, каждый как `модуль:Класс`. Перечисляются
    именно секции, а не один корневой класс: корень собирает их фабриками, и
    его собственные поля — это секции, а не переменные. Пустой список значит
    «ничего не собирать»: проект без настроек из окружения — обычное дело.

    `path` — куда писать; по умолчанию `.env.example` в корне.
    """

    settings: tuple[str, ...] = ()
    path: str = FILE


def example(*, config: Config) -> Example:
    try:
        return Example.model_validate(config.section(code=SECTION))
    except ValidationError as error:
        raise ConfigError(f"[{prefix(source=config.origin)}{SECTION}]: {error}") from error
