"""Протокол и алиас над ним."""

from typing import Protocol, TypeAlias


class BetWriter(Protocol):
    async def place(self, *, stake: int) -> None: ...


Writer: TypeAlias = BetWriter
Rows = dict[str, int]
