from decimal import Decimal

from shop.shared import money
from shop.shared.money import to_eur


class Ladder:
    def step(self, *, price: Decimal, rate: Decimal) -> Decimal:
        return to_eur(amount=price, rate=rate) + money.from_eur(amount=price, rate=rate)
