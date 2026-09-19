"""Сигнатуры и тела.

Длина модуля, глубина вложенности и требование писать сигнатуру полностью.
Длина функции, число аргументов и перенос аргументов закрываются правилами
ruff, вложенный `with` — правилом `SIM117`.
"""

from py_checks.checks.signatures._keyword_only import KeywordOnlyArguments
from py_checks.checks.signatures._marker import MARKER
from py_checks.checks.signatures._module_length import ModuleLength, ModuleLengthSettings
from py_checks.checks.signatures._nesting import Nesting, NestingSettings
from py_checks.checks.signatures._signature_layout import (
    SignatureLayout,
    SignatureLayoutSettings,
)

__all__ = [
    "MARKER",
    "KeywordOnlyArguments",
    "ModuleLength",
    "ModuleLengthSettings",
    "Nesting",
    "NestingSettings",
    "SignatureLayout",
    "SignatureLayoutSettings",
]
