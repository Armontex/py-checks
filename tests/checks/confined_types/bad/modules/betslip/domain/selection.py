"""Голые примитивы в домене."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class Selection:
    market: str
    odds: float
    version: int
    tags: tuple[str, ...]
