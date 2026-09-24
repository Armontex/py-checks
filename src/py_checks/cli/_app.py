"""The command-line application."""

from __future__ import annotations

import typer

from py_checks.cli.commands import REGISTRARS

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Checks of a project's architectural conventions.",
)

for register in REGISTRARS:
    register(app=app)


def main() -> None:
    """The entry point of the `py-checks` console command."""
    app()
