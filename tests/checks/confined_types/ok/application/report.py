"""Вне зоны: число на пути в отчёт — это арифметика."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class Report:
    share: float
    title: str
