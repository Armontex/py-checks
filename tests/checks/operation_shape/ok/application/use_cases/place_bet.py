"""Вход уместился в команду, а зависимости пришли конструктором."""

from typing import Protocol

Amount = int


class PlaceBetUseCase:
    def __init__(self, *, bets: Protocol, prices: Protocol, clock: Protocol) -> None:
        self._bets = bets
        self._prices = prices
        self._clock = clock

    async def execute(self, *, amount: Amount) -> bool:
        return self._judged(amount=amount)

    @staticmethod
    def _judged(*, amount: Amount) -> bool:
        return amount > 0
