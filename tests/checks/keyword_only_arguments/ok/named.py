"""Подписи, записанные полностью."""


def price(*, market: str, stake: int) -> str:
    return f"{market}{stake}"


class Rule:
    def apply(self, *, rule: str) -> str:
        return rule

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Rule)


def wrapper(constraint: str) -> str:  # signature-ok: подпись диктует sqlalchemy
    return constraint


def nothing() -> None:
    return None
