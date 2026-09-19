"""Строковые ключи и поход в базу на каждой итерации."""

from typing import Any, Protocol


class Statement:
    def on_conflict_do_update(self, **kwargs: Any) -> "Statement":  # noqa: ANN401
        del kwargs
        return self

    def from_select(self, columns: list[Any], select: Any) -> "Statement":  # noqa: ANN401
        del columns, select
        return self


class Session(Protocol):
    async def execute(self, statement: object) -> object: ...


class InboxRepository:
    def __init__(self, *, session: Session) -> None:
        self._session = session

    async def record(self, *, statement: Statement, handled_at: object) -> None:
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=["event_id"],
                set_={"handled_at": handled_at},
            ),
        )

    async def copy(self, *, statement: Statement, select: object) -> None:
        await self._session.execute(statement.from_select(["event_id", "handled_at"], select))

    async def each(self, *, events: list[object]) -> None:
        for event in events:
            await self._session.execute(event)
