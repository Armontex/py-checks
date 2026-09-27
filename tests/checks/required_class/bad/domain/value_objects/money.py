"""Рядом с `...Value` лёг голый `Price`."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PriceValue:
    amount: int


@dataclass(frozen=True, slots=True)
class Price:
    amount: int
