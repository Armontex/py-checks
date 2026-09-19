"""Места вызова.

Есть функции, у которых законных мест вызова ровно столько, сколько их
перечислено: конверсия денег, например. Правило держит этот список.
"""

from python_checks.checks.calls._confined_functions import (
    ConfinedFunctions,
    ConfinedFunctionsSettings,
)
from python_checks.checks.calls._marker import MARKER

__all__ = ["MARKER", "ConfinedFunctions", "ConfinedFunctionsSettings"]
