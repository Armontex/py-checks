"""Второй `try` внутри первого и третий уровень `if`."""


def handled(*, path: str) -> int:
    try:
        try:
            return int(path)
        except ValueError:
            return 0
    except OSError:
        return -1


def decided(*, first: int, second: int, third: int) -> bool:
    if first:
        if second:
            if third:
                return True
    return False


def written(*, code: int) -> str:
    if code > 0:
        return "плюс"
    else:
        if code < 0:
            if code < -10:
                return "много минус"
            return "минус"
    return "ноль"
