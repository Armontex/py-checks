"""Настройки, которые остались в `pyproject.toml` и больше не читаются."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

from python_checks.config import PYPROJECT
from python_checks.sync._managed import MANAGED

if TYPE_CHECKING:
    from pathlib import Path


def leftovers(*, root: Path) -> list[str]:
    """Секции `[tool.*]`, которые инструмент перестал видеть.

    И ruff, и pyright, найдя свой файл в корне, забывают про `pyproject.toml`
    целиком. Секция там остаётся выглядеть как настройка, но не значит уже
    ничего — самый тихий способ потерять послабление, о котором все помнят.
    """
    pyproject = root / PYPROJECT
    if not pyproject.is_file():
        return []
    tool = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("tool")
    if not isinstance(tool, dict):
        return []
    return [
        f"tool.{managed.section}"
        for managed in MANAGED
        if managed.section in tool and (root / managed.project).is_file()
    ]
