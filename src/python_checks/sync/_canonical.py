"""Чтение эталона из самой библиотеки."""

from __future__ import annotations

from importlib import resources

from python_checks.sync._constants import PACKAGE


def canonical(*, name: str) -> str:
    """Содержимое эталонного конфига, как он лежит в установленном пакете."""
    return resources.files(PACKAGE).joinpath(name).read_text(encoding="utf-8")
