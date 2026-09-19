"""Имя обещает константу, тип молчит."""

from decimal import Decimal

LIMIT = 50
TOPICS: tuple[str, ...] = ("orders", "bets")


class PositiveDecimal:
    BOUND = Decimal("0")
    SCALE: int = 2
