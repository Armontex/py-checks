"""Описание проверки, взятое из её докстринга."""

from __future__ import annotations

import inspect as introspect
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from python_checks.core import Check

NO_DOC: Final = "нет описания"


def docstring(*, check: Check) -> str:
    return introspect.getdoc(type(check)) or NO_DOC


def summary(*, check: Check) -> str:
    """Первая строка докстринга: правило одной фразой."""
    return docstring(check=check).splitlines()[0]
