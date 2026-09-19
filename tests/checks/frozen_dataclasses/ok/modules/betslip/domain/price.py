"""Значение: собрали один раз и не меняли."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class Price:
    amount: int
    currency: str


@dataclass(frozen=True, slots=True, kw_only=True)
class Stake:
    amount: int
