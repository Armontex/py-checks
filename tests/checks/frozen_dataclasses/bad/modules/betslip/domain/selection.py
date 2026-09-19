"""Изменяемое значение и значение без слотов."""

from dataclasses import dataclass


@dataclass
class Selection:
    market: str
    price: int


@dataclass(frozen=True)
class Outcome:
    name: str


@dataclass(frozen=False, slots=True)
class Draft:
    name: str
