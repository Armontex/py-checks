"""Сервис приложения лежит в application/services."""


class PricingService:
    def price(self, *, stake: int) -> int:
        return stake
