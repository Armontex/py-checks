"""Сигнатуры и тела.

Длина функции и модуля, глубина вложенности, требование писать сигнатуру
полностью и раскладывать её по столбцу. Число аргументов судит
`operation-shape` — там, где известно, какой класс операция и какая у неё
дверь; вложенный `with` отдан ruff, правилу `SIM117` с автофиксом.
"""

from py_checks.checks.signatures._function_length import (
    FunctionLength,
    FunctionLengthSettings,
)
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
    "FunctionLength",
    "FunctionLengthSettings",
    "KeywordOnlyArguments",
    "ModuleLength",
    "ModuleLengthSettings",
    "Nesting",
    "NestingSettings",
    "SignatureLayout",
    "SignatureLayoutSettings",
]
