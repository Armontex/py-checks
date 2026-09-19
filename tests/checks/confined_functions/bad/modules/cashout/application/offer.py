from decimal import Decimal

from shop.shared.money import to_eur


class OfferCashout:
    def __call__(self, *, stake: Decimal, rate: Decimal) -> Decimal:
        return to_eur(amount=stake, rate=rate)
