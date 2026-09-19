"""CHECK забыт, и CHECK, называющий другую границу."""

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
    market: Mapped[NonEmptyString]

    __table_args__ = (bound_check(column=market, primitive=PositiveDecimal),)
