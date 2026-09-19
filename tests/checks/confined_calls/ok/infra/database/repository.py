"""Репозиторий пишет через сессию, а границу оставляет вызывающему."""

from typing import Protocol


class Session(Protocol):
    def add(self, row: object) -> None: ...
    async def flush(self) -> None: ...


class OrderRepository:
    def __init__(self, *, session: Session) -> None:
        self._session = session

    async def save(self, *, row: object) -> None:
        self._session.add(row)
        await self._session.flush()
