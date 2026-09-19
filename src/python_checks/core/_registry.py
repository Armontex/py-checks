"""Какие проверки существуют и как их находят."""

from __future__ import annotations

from importlib.metadata import entry_points
from typing import TYPE_CHECKING

from python_checks.core._constants import GROUP, PROJECT_GROUP
from python_checks.core._errors import UnknownCheckError

if TYPE_CHECKING:
    from python_checks.core._protocols import FileCheck, ProjectCheck


def available() -> dict[str, FileCheck]:
    """Все проверки, объявленные через entry points.

    Так проект или команда добавляет своё правило: ставит рядом свой пакет с
    записью в этой же группе, а библиотеку форкать не нужно.
    """
    found: dict[str, FileCheck] = {}
    for entry in entry_points(group=GROUP):
        check = entry.load()()
        found[check.code] = check
    return found


def get(*, code: str) -> FileCheck:
    checks = available()
    if code not in checks:
        raise UnknownCheckError(
            code=code,
            known=tuple(sorted(checks)),
        )
    return checks[code]


def available_project() -> dict[str, ProjectCheck]:
    """Все правила, которым нужен проект целиком, а не файл."""
    found: dict[str, ProjectCheck] = {}
    for entry in entry_points(group=PROJECT_GROUP):
        check = entry.load()()
        found[check.code] = check
    return found


def get_project(*, code: str) -> ProjectCheck:
    checks = available_project()
    if code not in checks:
        raise UnknownCheckError(
            code=code,
            known=tuple(sorted(checks)),
        )
    return checks[code]
