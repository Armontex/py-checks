"""Сервис: дверей несколько, и это его форма."""


class PricingService:
    def opened(self, *, line: int) -> int:
        return line

    def settled(self, *, line: int) -> int:
        return line
