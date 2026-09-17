"""Приложение командной строки."""

from __future__ import annotations

import typer

from python_checks.cli.commands import REGISTRARS

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Проверки архитектурных соглашений проекта.",
)

for register in REGISTRARS:
    register(app=app)


def main() -> None:
    """Точка входа консольной команды `python-checks`."""
    app()
