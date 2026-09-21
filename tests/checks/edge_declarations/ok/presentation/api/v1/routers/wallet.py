"""Клиент соседа зовёт `.post(...)` — и это не маршрут, а исходящий запрос."""

from httpx import AsyncClient


async def top_up(*, client: AsyncClient, player: str) -> None:
    await client.post("/wallet/top-up", json={"player": player})
