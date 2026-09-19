"""Обе половины обещания на месте."""

from decimal import Decimal
from typing import Any

PositiveDecimal = Decimal
NonEmptyString = str


class Mapped[T]:
    pass


def bound_check(*, column: Any, primitive: Any) -> Any:  # noqa: ANN401
    return column, primitive


class BetModel:
    stake: Mapped[PositiveDecimal]
    market: Mapped[NonEmptyString | None]
    note: Mapped[str]

    __table_args__ = (
        bound_check(column=stake, primitive=PositiveDecimal),
        bound_check(column=market, primitive=NonEmptyString),
    )
