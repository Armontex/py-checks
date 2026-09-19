"""Описание проверки, взятое из её докстринга."""

from __future__ import annotations

import inspect as introspect
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from python_checks.core import FileCheck

NO_DOC: Final = "нет описания"


def docstring(*, check: FileCheck) -> str:
    return introspect.getdoc(type(check)) or NO_DOC


def summary(*, check: FileCheck) -> str:
    """Первая строка докстринга: правило одной фразой."""
    return docstring(check=check).splitlines()[0]
