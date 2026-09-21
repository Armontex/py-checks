"""Вне зоны: периметр разговаривает с чужим сервисом, а не с игроком."""


def parse(*, raw: str) -> int:
    if not raw.isdigit():
        raise ValueError(f"not a number: {raw}")
    return int(raw)
