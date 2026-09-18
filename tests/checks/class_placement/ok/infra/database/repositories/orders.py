"""Репозиторий лежит там, где база данных."""


class OrderRepository:
    async def add(self, *, stake: int) -> None: ...
