"""Имена и значения по умолчанию, общие для всего чтения настроек."""

from __future__ import annotations

SECTION = "python-checks"

DEFAULT_EXCLUDE: tuple[str, ...] = (
    ".venv/*",
    "build/*",
    "dist/*",
    "**/__pycache__/*",
    "**/migrations/versions/*",
)
