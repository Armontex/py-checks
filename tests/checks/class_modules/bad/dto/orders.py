"""Перечисление, забредшее в dto."""

from dataclasses import dataclass
from enum import StrEnum


class Status(StrEnum):
    PLACED = "placed"


@dataclass(frozen=True, slots=True)
class PlaceOrder:
    stake: int


class OrderMissing(Exception):
    """Отказу место в errors, а не рядом с данными."""
