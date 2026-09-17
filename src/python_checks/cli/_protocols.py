"""Каким приложение видит команду."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import typer


class Registrar(Protocol):
    """Функция, которая вешает команду на приложение.

    Только так `_app` и знает о командах: имя, опции и справка остаются в
    модуле команды, а приложение получает готовую регистрацию. Подпись одна и
    та же и для `app.command(...)`, и для `app.add_typer(...)`.
    """

    def __call__(self, *, app: typer.Typer) -> None: ...
