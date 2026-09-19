"""Конструктор — проводка, а вход уместился в команду."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlaceBetCommand:
    market: str
    stake: int
    currency: str
    idempotency_key: str


class PlaceBetUseCase:
    def __init__(self, *, bets: object, prices: object, clock: object, log: object) -> None:
        self._bets = bets
        self._prices = prices
        self._clock = clock
        self._log = log

    def execute(self, *, command: PlaceBetCommand) -> bool:
        return bool(self._bets and command)


def assembled(*, first: int, second: int, third: int, fourth: int) -> int:
    """Функция рядом не судится: правило про вход сценария."""
    return first + second + third + fourth
