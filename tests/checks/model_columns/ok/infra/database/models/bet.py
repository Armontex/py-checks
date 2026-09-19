"""Материал назван правилом, время со смещением, значения пишет запрос."""

from datetime import datetime
from decimal import Decimal
from typing import Any

PositiveDecimal = Decimal
NonEmptyString = str


class Mapped[T]:
    pass


def mapped_column(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
    return args, kwargs


def DateTime(*, timezone: bool = False) -> Any:  # noqa: ANN401, N802
    return timezone


def stored_enum(values: Any) -> Any:  # noqa: ANN401
    return values


class BetModel:
    stake: Mapped[PositiveDecimal] = mapped_column(nullable=False)
    market: Mapped[NonEmptyString | None] = mapped_column(nullable=True)
    placed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[NonEmptyString] = mapped_column(stored_enum(("won", "lost")))
