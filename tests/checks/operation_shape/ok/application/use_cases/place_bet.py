"""Сценарий: одна дверь, всё остальное приватно."""

from typing import Protocol

Amount = int


class PlaceBetUseCase:
    def __init__(self, *, bets: Protocol) -> None:
        self._bets = bets

    async def execute(self, *, amount: Amount) -> bool:
        return self._judged(amount=amount)

    @staticmethod
    def _judged(*, amount: Amount) -> bool:
        return amount > 0
