"""Подписи, которые правило отвергает."""


def price(market: str, stake: int) -> str:
    return f"{market}{stake}"


class Rule:
    def __init__(self, name: str) -> None:
        self.name = name

    def apply(self, rule: str) -> str:
        return rule


def collect(*args: str, **kwargs: str) -> None:
    return None


def spread(
    first: str,
    second: str,
) -> None:
    return None


class Static:
    @staticmethod
    def parse(self: str) -> str:
        return self


def handler(self: str) -> str:
    return self


class Outer:
    def method(self) -> str:
        def inner(self: str) -> str:
            return self

        return inner(self="x")
