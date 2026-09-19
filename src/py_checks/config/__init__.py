"""Настройки из `pyproject.toml` проекта.

Настройки живут либо в своём файле — `py-checks.toml` или `pychecks.toml`,
с точкой в начале или без, — либо секцией `[tool.py-checks]` в
`pyproject.toml`. В своём
файле приставки нет: весь файл и есть эта секция. Внутри — по секции на
проверку, и каждая описана моделью pydantic, поэтому опечатка в названии
настройки падает сразу и с понятным текстом.
"""

from py_checks.config._base import CheckSettings
from py_checks.config._config import Config, prefix
from py_checks.config._constants import DEFAULT_EXCLUDE, PYPROJECT, SECTION, STANDALONE
from py_checks.config._errors import ConfigError
from py_checks.config._loader import find_root, load
from py_checks.config._toml import TomlTable, TomlValue

__all__ = [
    "DEFAULT_EXCLUDE",
    "PYPROJECT",
    "SECTION",
    "STANDALONE",
    "CheckSettings",
    "Config",
    "ConfigError",
    "TomlTable",
    "TomlValue",
    "find_root",
    "load",
    "prefix",
]
