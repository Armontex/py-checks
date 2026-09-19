"""Всё в столбик, а чужая позиционная подпись не трогается."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Money:
    amount: int
    currency: str


def price(
    *,
    market: str,
    stake: Money,
) -> Money:
    del market
    return stake


def single(*, stake: Money) -> Money:
    return stake


def bought(*, market: str) -> Money:
    return price(
        market=market,
        stake=Money(
            amount=1,
            currency="RUB",
        ),
    )


def counted(*, values: list[int]) -> int:
    return min(len(values), max(1, 10))
