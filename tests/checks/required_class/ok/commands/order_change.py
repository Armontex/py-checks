"""Ленивый `type` стоит первым, его части — ниже."""

from dataclasses import dataclass
from uuid import UUID

type OrderChangeCommand = OrderPlaced | OrderCancelled


@dataclass(frozen=True, slots=True, kw_only=True)
class OrderPlaced:
    order_id: UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class OrderCancelled:
    order_id: UUID
    reason: str
