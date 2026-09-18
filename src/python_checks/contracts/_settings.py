"""Слои проекта: что он объявил о себе сам."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import ValidationError

from python_checks.config import CheckSettings, ConfigError
from python_checks.contracts._constants import SECTION

if TYPE_CHECKING:
    from python_checks.config import Config


class Contracts(CheckSettings):
    """Секция `[tool.python-checks.contracts]`.

    `layers` — слой и то, что ему разрешено импортировать. Всё, чего в таблице
    нет, ограничений не имеет: библиотека не знает, как называются слои в этом
    проекте, и не догадывается за него.

    `composition-root` — слои, которым можно всё: они связывают остальные между
    собой, и это вся их работа. Перечислять их отдельно нужно затем, чтобы они
    попали в запреты остальных: слой, о котором таблица не знает, ничьим
    запретом не становится.
    """

    composition_root: tuple[str, ...] = ()
    layers: dict[str, tuple[str, ...]] = {}


def contracts(*, config: Config) -> Contracts:
    try:
        return Contracts.model_validate(config.section(code=SECTION))
    except ValidationError as error:
        raise ConfigError(f"[tool.python-checks.{SECTION}]: {error}") from error
