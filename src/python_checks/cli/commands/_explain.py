"""Команда `explain`: подробности об одной проверке."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console

from python_checks.cli.commands._summary import docstring
from python_checks.core import get


def explain(
    code: Annotated[str, typer.Argument(help="код проверки")],
) -> None:
    """Показать, что проверка требует и какие у неё настройки."""
    check = get(code)
    console = Console()
    console.print(docstring(check), markup=False)
    console.print("\nнастройки:", markup=False)
    for name, field in check.Settings.model_fields.items():
        key = field.alias or name
        console.print(f"  {key} = {field.get_default(call_default_factory=True)!r}", markup=False)
