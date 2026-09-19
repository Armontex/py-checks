"""Изменяемое значение и значение без слотов."""

from dataclasses import dataclass


@dataclass
class Selection:
    market: str
    price: int


@dataclass(frozen=True)
class Outcome:
    name: str


@dataclass(frozen=False, slots=True, kw_only=True)
class Draft:
    name: str


@dataclass(frozen=True, slots=True)
class Ticket:
    """Два поля одного типа: без `kw_only` их порядок помнит только автор."""

    market: str
    outcome: str
