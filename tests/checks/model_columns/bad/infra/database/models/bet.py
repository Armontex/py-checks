"""Материал, который колонке не положен."""

from datetime import datetime
from decimal import Decimal
from typing import Any


class Mapped[T]:
    pass


def mapped_column(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
    return args, kwargs


def DateTime(*, timezone: bool = False) -> Any:  # noqa: ANN401, N802
    return timezone


def Enum(*values: str) -> Any:  # noqa: ANN401, N802
    return values


def Float() -> Any:  # noqa: ANN401, N802
    return None


class BetModel:
    stake: Mapped[Decimal] = mapped_column(Float())
    status: Mapped[str] = mapped_column(Enum("won", "lost"))
    placed_at: Mapped[datetime] = mapped_column(DateTime(), server_default="now()")
    market: Mapped[str | None] = mapped_column(nullable=False)
