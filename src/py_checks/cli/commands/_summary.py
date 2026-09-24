"""A check's description, taken from its docstring."""

from __future__ import annotations

import inspect as introspect
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from py_checks.core import Check

NO_DOC: Final = "no description"


def docstring(*, check: Check) -> str:
    return introspect.getdoc(type(check)) or NO_DOC


def summary(*, check: Check) -> str:
    """The first line of the docstring: the rule in one sentence."""
    return docstring(check=check).splitlines()[0]
