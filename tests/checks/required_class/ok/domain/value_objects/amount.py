"""База объявлена в другом модуле, суффикс на месте."""

from shared.values import FrozenValue


class AmountValue(FrozenValue):
    cents: int
