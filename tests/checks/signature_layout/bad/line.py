"""Подпись и вызов в строку."""

Money = int


def price(*, market: str, stake: Money = 1) -> Money:
    del market
    return stake


def bought(*, market: str) -> Money:
    return price(market=market, stake=2)
