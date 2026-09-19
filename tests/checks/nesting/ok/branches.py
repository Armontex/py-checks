"""`elif` — ветка, а не уровень, и двух `if` достаточно."""


def judged(*, first: int, second: int) -> str:
    if first > 0:
        if second > 0:
            return "оба"
        return "первый"
    if first < 0:
        return "минус"
    return "ноль"


def named(*, code: int) -> str:
    if code == 1:
        return "один"
    elif code == 2:
        return "два"
    elif code == 3:
        return "три"
    return "другое"


def guarded(*, path: str) -> int:
    try:
        return int(path)
    except ValueError:
        return 0
    finally:
        del path
