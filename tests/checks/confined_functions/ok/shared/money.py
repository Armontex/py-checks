from decimal import Decimal


def to_eur(*, amount: Decimal, rate: Decimal) -> Decimal:
    return amount * rate


def from_eur(*, amount: Decimal, rate: Decimal) -> Decimal:
    return amount / rate
