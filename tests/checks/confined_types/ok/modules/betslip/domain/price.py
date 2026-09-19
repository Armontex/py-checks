"""Тип называет, что значение может держать."""

from dataclasses import dataclass
from typing import ClassVar, NewType

from decimal import Decimal

Amount = NewType("Amount", Decimal)
Currency = NewType("Currency", str)


@dataclass(frozen=True, slots=True, kw_only=True)
class Price:
    amount: Amount
    currency: Currency

    BOUND: ClassVar[Decimal] = Decimal("0.01")
