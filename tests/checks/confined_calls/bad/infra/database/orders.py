"""Коммит в середине превращает одну транзакцию в три."""

from typing import Protocol


class Session(Protocol):
    def add(self, row: object) -> None: ...
    async def commit(self) -> None: ...
    def begin_nested(self) -> object: ...


class OrderRepository:
    def __init__(self, *, session: Session) -> None:
        self._session = session

    async def save(self, *, row: object) -> None:
        self._session.add(row)
        await self._session.commit()

    def savepoint(self) -> object:
        return self._session.begin_nested()
