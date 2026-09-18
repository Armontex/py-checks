"""Отказы и заехавший к ним хелпер."""


class OrderError(Exception):
    """Корень отказов модуля."""


def refused(*, order: str) -> OrderError:
    return OrderError(order)
