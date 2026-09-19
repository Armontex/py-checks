"""Обещание сказано типом."""

from decimal import Decimal
from enum import StrEnum
from typing import ClassVar, Final

LIMIT: Final = 50
TOPICS: Final[tuple[str, ...]] = ("orders", "bets")

lowercase_is_a_variable = 1


class Outcome(StrEnum):
    WON = "won"
    LOST = "lost"


class PositiveDecimal:
    BOUND: ClassVar[Decimal] = Decimal("0")

    def __init__(self, *, value: Decimal) -> None:
        self.value = value
