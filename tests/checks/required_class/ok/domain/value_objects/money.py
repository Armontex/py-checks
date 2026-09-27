"""Два значения одной идеи в одном модуле: суффикс у обоих."""

from dataclasses import dataclass
from enum import StrEnum


class Currency(StrEnum):
    EUR = "EUR"


@dataclass(frozen=True, slots=True)
class PriceValue:
    amount: int


@dataclass(frozen=True, slots=True)
class CurrencyValue:
    code: Currency


@dataclass(frozen=True, slots=True)
class _Cents:
    whole: int
