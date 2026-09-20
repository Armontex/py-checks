"""Команда `explain`: подробности об одной проверке."""

from __future__ import annotations

import typing
from typing import Annotated, Final

import typer
from pydantic import BaseModel
from rich.console import Console

from py_checks.cli.commands._summary import docstring
from py_checks.core import get, section_of

EXTRA: Final = "__pydantic_extra__"


def explain(  # check-ok: keyword-only-arguments: подпись команды разбирает typer
    code: Annotated[str, typer.Argument(help="код проверки")],
) -> None:
    """Показать, что проверка требует и какие у неё настройки."""
    check = get(code=code)
    console = Console()
    console.print(docstring(check=check), markup=False)
    section = section_of(check=check)
    shared = " (общая)" if section != check.code else ""
    console.print(f"\nнастройки, секция [{section}]{shared}:", markup=False)
    fields = _fields(model=check.Settings)
    for name, field in fields.items():
        key = field.alias or name
        console.print(f"  {key} = {field.get_default(call_default_factory=True)!r}", markup=False)
    if not fields:
        console.print(f"  <ключ проекта> = {_shape(model=check.Settings)}", markup=False)


def _fields(*, model: type[BaseModel]) -> dict[str, typing.Any]:  # noqa: ANN401
    """Поля модели, а у таблицы с ключами проекта — поля одного её блока.

    Секция, ключи которой приносит проект (адреса директорий, имена пакетов),
    своих полей не имеет: объявлять там нечего, кроме того, из чего состоит
    блок. Печатать пустой список значит сказать «настроек нет», а они есть.
    """
    if model.model_fields:
        return dict(model.model_fields)
    inner = _value(model=model)
    if isinstance(inner, type) and issubclass(inner, BaseModel):
        return dict(inner.model_fields)
    return {}


def _shape(*, model: type[BaseModel]) -> str:
    """Чем бывает значение под ключом проекта, когда это не блок, а список."""
    inner = _value(model=model)
    return inner.__name__ if isinstance(inner, type) else str(inner)


def _value(*, model: type[BaseModel]) -> typing.Any:  # noqa: ANN401
    """Тип значения в таблице, ключи которой приносит проект."""
    values = typing.get_args(typing.get_type_hints(model).get(EXTRA))
    return values[1] if len(values) == 2 else None  # noqa: PLR2004 — ключ и значение


def register(*, app: typer.Typer) -> None:
    app.command("explain")(explain)
