"""В домене dataclass законен, а отказ — нет."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Money:
    amount: int


class MoneyError(Exception):
    """Отказу место в errors."""
