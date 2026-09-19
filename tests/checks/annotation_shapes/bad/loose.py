"""Поля без имён: строковый ключ и позиция."""


def built() -> dict[str, object]:
    return {}


def paired(*, row: tuple[str, int]) -> int:
    return len(row)


def collected(*, rows: list[dict[str, str]]) -> int:
    return len(rows)
