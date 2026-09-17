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


def listener(target: str, value: str) -> None:  # check-ok: keyword-only-arguments: зовёт sqlalchemy
    return None


def legacy(target: str) -> None:  # signature-ok: старое слово из проекта
    return None


def column(
    first: str,
    second: str,
) -> None:  # check-ok: keyword-only-arguments: маркер на конце подписи в столбик
    return None


class Static:
    @staticmethod
    def build(*, value: str) -> str:
        return value

    @classmethod
    def make(cls, *, value: str) -> str:
        return value

    def rename(instance, *, value: str) -> str:  # первый аргумент передаёт интерпретатор
        return f"{instance}{value}"
