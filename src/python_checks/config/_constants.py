"""Имена и значения по умолчанию, общие для всего чтения настроек."""

from __future__ import annotations

from typing import Final

PYPROJECT: Final = "pyproject.toml"

SECTION: Final = "python-checks"

DEFAULT_EXCLUDE: Final[tuple[str, ...]] = (
    ".venv/*",
    "build/*",
    "dist/*",
    "**/__pycache__/*",
    "**/migrations/versions/*",
)
