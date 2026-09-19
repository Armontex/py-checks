"""Край брокера: здесь подтверждают смещение, а не транзакцию."""

from typing import Protocol


class Client(Protocol):
    async def commit(self, offsets: dict[int, int]) -> None: ...


class Offsets:
    def __init__(self, *, client: Client) -> None:
        self._client = client

    async def handled(self, *, partition: int, offset: int) -> None:
        await self._client.commit({partition: offset + 1})
