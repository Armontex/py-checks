"""The settings from the project's `pyproject.toml`.

The settings live either in the tool's own file — `py-checks.toml` or
`pychecks.toml`, with or without a leading dot — or as the `[tool.py-checks]`
section in `pyproject.toml`. The tool's own file has no prefix: the whole
file is that section. Inside there is one section per check, each described
by a pydantic model, so a typo in a setting's name fails at once and with a
clear message.
"""

from py_checks.config._base import OPEN, CheckSettings
from py_checks.config._config import Config, prefix
from py_checks.config._constants import DEFAULT_EXCLUDE, PYPROJECT, SECTION, STANDALONE
from py_checks.config._errors import ConfigError
from py_checks.config._loader import find_root, load
from py_checks.config._toml import TomlTable, TomlValue

__all__ = [
    "DEFAULT_EXCLUDE",
    "OPEN",
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
