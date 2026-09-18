"""Сценарий, названный именем файла."""

from enum import StrEnum


class Outcome(StrEnum):
    """Словарь, который сценарий называет у себя в теле."""

    PLACED = "placed"
    REJECTED = "rejected"


class PlaceBetUseCase:
    default = Outcome.PLACED

    def execute(self) -> Outcome:
        return self.default

    @staticmethod
    def _rounded(*, amount: int) -> int:
        return amount
