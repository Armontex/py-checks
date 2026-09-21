"""Ошибки.

Отказ, который модуль говорит наружу, несёт код: фраза — человеку, код — тому,
кто на него ветвится.
"""

from py_checks.checks.errors._marker import MARKER
from py_checks.checks.errors._refusals import Refusals, RefusalsSettings

__all__ = ["MARKER", "Refusals", "RefusalsSettings"]
