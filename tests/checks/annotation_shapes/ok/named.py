"""Имена у полей есть, а настоящий мешок ключей помечен."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class Row:
    market: str
    stake: int


def tagged(*, values: tuple[str, ...]) -> list[str]:
    return list(values)


def carried() -> dict[str, str]:  # type-ok: annotation-shapes: своя форма у propagator
    return {}


def counted(*, rows: dict[int, Row]) -> int:
    return len(rows)
