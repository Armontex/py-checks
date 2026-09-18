"""Доменный value object — тоже dataclass, но живёт в домене."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Money:
    amount: int
