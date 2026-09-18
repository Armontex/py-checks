"""Обычный класс в директории портов."""

from typing import Protocol


class BetWriter(Protocol):
    async def place(self, *, stake: int) -> None: ...


class InMemoryWriter:  # placement-ok: пример пометки на месте
    async def place(self, *, stake: int) -> None: ...


class SecondWriter:
    async def place(self, *, stake: int) -> None: ...
