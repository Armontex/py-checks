"""Данные приложения лежат в dto."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlaceOrder:
    stake: int
