"""Сигнатуры и тела.

Длина модуля, глубина вложенности и требование писать сигнатуру полностью.
Длина функции и перенос аргументов закрываются правилами ruff, вложенный
`with` — правилом `SIM117`.
"""

from python_checks.checks.signatures._argument_count import (
    ArgumentCount,
    ArgumentCountSettings,
    Subject,
)
from python_checks.checks.signatures._keyword_only import KeywordOnlyArguments
from python_checks.checks.signatures._module_length import ModuleLength, ModuleLengthSettings
from python_checks.checks.signatures._nesting import Nesting, NestingSettings

__all__ = [
    "ArgumentCount",
    "ArgumentCountSettings",
    "KeywordOnlyArguments",
    "ModuleLength",
    "ModuleLengthSettings",
    "Nesting",
    "NestingSettings",
    "Subject",
]
