"""Гигиена репозитория.

Зависимость объявляет потолок: без него версию выбирает решатель, а не
человек. Остальное этой группы закрывается не проверками — `.env.example`
генерируется из моделей настроек, а `CLAUDE.md` это симлинк на `AGENTS.md`.
"""

from py_checks.checks.hygiene._dependency_bounds import (
    DependencyBounds,
    DependencyBoundsSettings,
)
from py_checks.checks.hygiene._marker import MARKER

__all__ = ["MARKER", "DependencyBounds", "DependencyBoundsSettings"]
