"""Директории нет в таблице — правило молчит."""


def within(*, amount: int, cap: int) -> bool:
    return amount <= cap
