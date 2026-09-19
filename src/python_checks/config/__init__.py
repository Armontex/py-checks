"""Настройки из `pyproject.toml` проекта.

Настройки живут либо в своём файле — `python-checks.toml` или `pychecks.toml`,
с точкой в начале или без, — либо секцией `[tool.python-checks]` в
`pyproject.toml`. В своём
файле приставки нет: весь файл и есть эта секция. Внутри — по секции на
проверку, и каждая описана моделью pydantic, поэтому опечатка в названии
настройки падает сразу и с понятным текстом.
"""

from python_checks.config._base import CheckSettings
from python_checks.config._config import Config, prefix
from python_checks.config._constants import DEFAULT_EXCLUDE, PYPROJECT, SECTION, STANDALONE
from python_checks.config._errors import ConfigError
from python_checks.config._loader import find_root, load
from python_checks.config._toml import TomlTable, TomlValue

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
