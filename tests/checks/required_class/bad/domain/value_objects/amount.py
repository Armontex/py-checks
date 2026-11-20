"""База объявлена в другом модуле: вид класса из файла не виден, а суффикса нет."""

from shared.values import FrozenValue


class Amount(FrozenValue):
    cents: int
