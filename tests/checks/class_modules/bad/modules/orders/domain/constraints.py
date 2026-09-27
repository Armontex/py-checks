"""В модуль констант пробрались функция, класс и алиас."""

from typing import Final

MAX_NAME: Final[int] = 200

Row = dict[str, int]


def clamp(value: int) -> int:
    return min(value, MAX_NAME)


class Limits:
    top = MAX_NAME
