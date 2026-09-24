"""Signatures and bodies.

The length of a function and of a module, the depth of nesting, and the
demand that a signature is written out in full and laid out in a column. The
number of arguments is judged by `operation-shape`, where it is known which
class is the operation and what its door is; a nested `with` is left to ruff,
to `SIM117` with its autofix.
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
