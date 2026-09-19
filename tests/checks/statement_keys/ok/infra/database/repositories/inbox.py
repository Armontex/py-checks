"""Колонки названы атрибутами, а в базу ходим один раз."""

from typing import Any, Protocol


class Model:
    event_id = "event_id"
    handled_at = "handled_at"


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
                index_elements=[Model.event_id],
                set_={Model.handled_at: handled_at},
            ),
        )

    async def each(self, *, names: tuple[str, ...]) -> None:
        for name in names:  # db-ok: statement-keys: три константы, множества нет
            await self._session.execute(name)
