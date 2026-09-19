"""Владелец границы: здесь вызов и должен стоять."""

from typing import Protocol


class Session(Protocol):
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


class UnitOfWork:
    def __init__(self, *, session: Session) -> None:
        self._session = session

    async def done(self) -> None:
        await self._session.commit()

    async def failed(self) -> None:
        await self._session.rollback()
