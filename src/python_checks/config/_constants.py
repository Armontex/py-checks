"""Имена и значения по умолчанию, общие для всего чтения настроек."""

from __future__ import annotations

from typing import Final

PYPROJECT: Final = "pyproject.toml"

SECTION: Final = "python-checks"

# Свой файл настроек — как у ruff и mypy: назван именем инструмента, с точкой
# в начале и без. В нём приставки `[tool.python-checks]` нет: весь файл и есть
# эта секция, а `[<код>]` в нём — секция проверки.
#
# Имён четыре: полное и короткое, каждое с точкой и без. Угадывать, как проект
# назовёт свой файл, дешевле, чем отказывать ему за не ту букву, — а лежать
# сразу двум файлам всё равно запрещено.
STANDALONE: Final[tuple[str, ...]] = (
    ".python-checks.toml",
    "python-checks.toml",
    ".pychecks.toml",
    "pychecks.toml",
)

DEFAULT_EXCLUDE: Final[tuple[str, ...]] = (
    ".venv/*",
    "build/*",
    "dist/*",
    "**/__pycache__/*",
    "**/migrations/versions/*",
)
