"""Границы выражены выражением, а проба живости помечена."""

from decimal import Decimal
from typing import Any


def CheckConstraint(expression: Any, name: str = "") -> Any:  # noqa: ANN401, N802
    del name
    return expression


def text(statement: str) -> str:
    return statement


def and_(*parts: Any) -> Any:  # noqa: ANN401
    return parts


NOTHING = Decimal("0")
WHOLE = Decimal("1")


class MarginModel:
    margin = Decimal("0.5")

    __table_args__ = (CheckConstraint(and_(margin >= NOTHING, margin < WHOLE)),)


def alive() -> str:
    return text("SELECT 1")  # db-ok: raw-sql: проба живости, формы ORM нет
