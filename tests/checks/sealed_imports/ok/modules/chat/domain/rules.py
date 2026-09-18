"""Правила знают стандартную библиотеку и свой код."""

from dataclasses import dataclass
from decimal import Decimal

from ok.shared.money import Money

__all__ = ["Decimal", "Money", "dataclass"]
