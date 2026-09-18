"""Порт на месте, а репозиторий рядом — нет."""

from typing import Protocol


class BetWriter(Protocol):
    async def place(self, *, stake: int) -> None: ...


class OrderRepository:  # placement-ok: пример пометки на месте
    async def add(self, *, stake: int) -> None: ...
