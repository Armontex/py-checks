"""Вход разросся в четыре параметра, а сборщик считается за один."""


class SettleBetUseCase:
    def execute(self, *, bet: str, outcome: str, amount: int, settled_at: str) -> bool:
        return bool(bet and outcome and amount and settled_at)

    @staticmethod
    def rounded(self: object, amount: int, precision: int, mode: str) -> int:
        """`self` в `@staticmethod` — обычный аргумент, и он считается."""
        del self, mode
        return amount * precision

    def reported(self, *fields: str, **extra: str) -> int:
        return len(fields) + len(extra) + len(self.__dict__)
