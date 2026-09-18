"""Данные и объединение над ними."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlaceOrder:
    stake: int


@dataclass(frozen=True, slots=True)
class CancelOrder:
    order: str


Order = PlaceOrder | CancelOrder
