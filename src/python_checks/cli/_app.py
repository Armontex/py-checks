"""Приложение командной строки."""

from __future__ import annotations

import typer

from python_checks.cli.commands import explain, list_checks, run

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Проверки архитектурных соглашений проекта.",
)

app.command("run")(run)
app.command("list")(list_checks)
app.command("explain")(explain)


def main() -> None:
    """Точка входа консольной команды `python-checks`."""
    app()
