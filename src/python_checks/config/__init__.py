"""Настройки из `pyproject.toml` проекта.

Секция `[tool.python-checks]` и по секции на проверку. Каждая описана моделью
pydantic, поэтому опечатка в названии настройки падает сразу и с понятным
текстом.
"""

from python_checks.config._base import CheckSettings
from python_checks.config._settings import (
    DEFAULT_EXCLUDE,
    SECTION,
    Config,
    ConfigError,
    find_root,
    load,
)

__all__ = [
    "DEFAULT_EXCLUDE",
    "SECTION",
    "CheckSettings",
    "Config",
    "ConfigError",
    "find_root",
    "load",
]
