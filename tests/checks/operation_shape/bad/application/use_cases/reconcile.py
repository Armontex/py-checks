"""Вход разросся в четыре поля: это команда, а не четыре параметра."""


class ReconcileUseCase:
    def execute(self, *, bet: str, outcome: str, amount: int, at: str) -> bool:
        return bool(bet and outcome and amount and at)
