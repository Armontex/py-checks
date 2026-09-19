"""Правило, записанное второй раз на языке, который никто не проверяет."""

from typing import Any


def CheckConstraint(expression: Any, name: str = "") -> Any:  # noqa: ANN401, N802
    del name
    return expression


def text(statement: str) -> str:
    return statement


class MarginModel:
    __table_args__ = (CheckConstraint("margin >= 0 AND margin < 1"),)


def counted(*, table: str) -> str:
    return text(f"SELECT count(*) FROM {table}")
