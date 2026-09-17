"""Настройки из `pyproject.toml` проекта.

Секция `[tool.python-checks]` и по секции на проверку. Каждая описана моделью
pydantic, поэтому опечатка в названии настройки падает сразу и с понятным
текстом.
"""

from python_checks.config._base import CheckSettings
from python_checks.config._config import Config
from python_checks.config._constants import DEFAULT_EXCLUDE, PYPROJECT, SECTION
from python_checks.config._errors import ConfigError
from python_checks.config._loader import find_root, load
from python_checks.config._toml import TomlTable, TomlValue

__all__ = [
    "DEFAULT_EXCLUDE",
    "PYPROJECT",
    "SECTION",
    "CheckSettings",
    "Config",
    "ConfigError",
    "TomlTable",
    "TomlValue",
    "find_root",
    "load",
]
