"""Репозиторий, и ниже — его хелпер."""


class OrderRepository:
    def get(self, *, order: int) -> int:
        return _doubled(value=order)


def _doubled(*, value: int) -> int:
    return value * 2
