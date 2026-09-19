from decimal import Decimal


class Ladder:
    def step(self, *, price: Decimal) -> Decimal:
        return price * Decimal("1.05")
