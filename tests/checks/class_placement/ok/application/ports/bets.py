"""Порт лежит в ports."""

from typing import Protocol


class BetWriter(Protocol):
    async def place(self, *, stake: int) -> None: ...
