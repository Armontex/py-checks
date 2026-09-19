from decimal import Decimal

from shop.shared.money import from_eur, to_eur


class OfferCashout:
    def __call__(self, *, stake: Decimal, rate: Decimal) -> Decimal:
        inside = to_eur(amount=stake, rate=rate)
        return from_eur(amount=inside * 2, rate=rate)
