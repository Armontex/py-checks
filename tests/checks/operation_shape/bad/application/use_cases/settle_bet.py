"""Словарь встал рядом с операцией, а транзакцию она держит сама."""

from enum import StrEnum


class Outcome(StrEnum):
    WON = "won"


class SettleBetUseCase:
    def __init__(self, *, uow: "PlacementUnitOfWork") -> None:
        self._uow = uow

    def execute(self) -> Outcome:
        return Outcome.WON
