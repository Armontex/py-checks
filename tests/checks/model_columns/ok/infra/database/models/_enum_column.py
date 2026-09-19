"""Дом обёртки над Enum: здесь его называть можно."""

from typing import Any


def Enum(*values: str) -> Any:  # noqa: ANN401, N802
    return values


def stored_enum(values: tuple[str, ...]) -> Any:  # noqa: ANN401
    return Enum(*values)
