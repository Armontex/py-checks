"""Слои проекта: база библиотеки плюс то, чем проект от неё отличается."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import RootModel, ValidationError

from python_checks.config import ConfigError, TomlTable
from python_checks.contracts._base import BASE
from python_checks.contracts._constants import SECTION

if TYPE_CHECKING:
    from python_checks.config import Config


class Override(RootModel[dict[str, tuple[str, ...]]]):
    """Секция `[tool.python-checks.layers]`: слой — что ему можно импортировать.

    Перечисляется только отличие. Слой, которого нет в базе, добавляется;
    слой, который есть, переписывается целиком — половинчатое «добавь ещё
    один разрешённый» пришлось бы читать вместе с базой, чтобы понять правило.
    """

    root: dict[str, tuple[str, ...]] = {}


def layers(*, config: Config) -> dict[str, frozenset[str]]:
    section: TomlTable = config.section(code=SECTION)
    try:
        override = Override.model_validate(section)
    except ValidationError as error:
        raise ConfigError(f"[tool.python-checks.{SECTION}]: {error}") from error
    return {**BASE, **{layer: frozenset(allowed) for layer, allowed in override.root.items()}}
