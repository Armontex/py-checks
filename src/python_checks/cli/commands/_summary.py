"""Описание проверки, взятое из её докстринга."""

from __future__ import annotations

import inspect as introspect
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from python_checks.core import FileCheck

NO_DOC = "нет описания"


def docstring(check: FileCheck) -> str:
    return introspect.getdoc(type(check)) or NO_DOC


def summary(check: FileCheck) -> str:
    """Первая строка докстринга: правило одной фразой."""
    return docstring(check).splitlines()[0]
