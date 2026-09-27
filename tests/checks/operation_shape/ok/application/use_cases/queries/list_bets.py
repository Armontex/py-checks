"""Запрос берёт запрос."""

from application.dto.queries import ListBetsQuery


class ListBetsUseCase:
    async def execute(self, *, query: ListBetsQuery) -> int:
        return query.limit
