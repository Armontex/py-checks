"""The `explain` command: the details of one check."""

from __future__ import annotations

import typing
from typing import Annotated, Final

import typer
from pydantic import BaseModel
from rich.console import Console

from py_checks.cli.commands._summary import docstring
from py_checks.core import get, section_of

EXTRA: Final = "__pydantic_extra__"


def explain(  # check-ok: keyword-only-arguments: typer parses the command's signature
    code: Annotated[str, typer.Argument(help="the check's code")],
) -> None:
    """Show what a check asks for and what settings it has."""
    check = get(code=code)
    console = Console()
    console.print(docstring(check=check), markup=False)
    section = section_of(check=check)
    shared = " (shared)" if section != check.code else ""
    console.print(f"\nsettings, section [{section}]{shared}:", markup=False)
    fields = _fields(model=check.Settings)
    for name, field in fields.items():
        key = field.alias or name
        console.print(f"  {key} = {field.get_default(call_default_factory=True)!r}", markup=False)
    if not fields:
        console.print(f"  <project key> = {_shape(model=check.Settings)}", markup=False)


def _fields(*, model: type[BaseModel]) -> dict[str, typing.Any]:  # noqa: ANN401
    """The model's fields; for a table with project keys, the fields of one block.

    A section whose keys the project brings (directory paths, package names)
    has no fields of its own: there is nothing to declare there but what a
    block is made of. Printing an empty list would say "no settings", and there
    are some.
    """
    if model.model_fields:
        return dict(model.model_fields)
    inner = _value(model=model)
    if isinstance(inner, type) and issubclass(inner, BaseModel):
        return dict(inner.model_fields)
    return {}


def _shape(*, model: type[BaseModel]) -> str:
    """What a value under a project key can be, when it is a list, not a block."""
    inner = _value(model=model)
    return inner.__name__ if isinstance(inner, type) else str(inner)


def _value(*, model: type[BaseModel]) -> typing.Any:  # noqa: ANN401
    """The type of a value in a table whose keys the project brings."""
    values = typing.get_args(typing.get_type_hints(model).get(EXTRA))
    return values[1] if len(values) == 2 else None  # noqa: PLR2004 — a key and a value


def register(*, app: typer.Typer) -> None:
    app.command("explain")(explain)
