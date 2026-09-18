"""Всё не на своих местах."""

from dataclasses import dataclass
from typing import Protocol


class BetWriter(Protocol):
    async def place(self, *, stake: int) -> None: ...


@dataclass(frozen=True, slots=True)
class PlaceOrder:
    stake: int


class PlaceBetUseCase:
    async def execute(self, *, stake: int) -> int:
        return stake


class PricingService:
    def price(self, *, stake: int) -> int:
        return stake


class OrderRepository:
    async def add(self, *, stake: int) -> None: ...
