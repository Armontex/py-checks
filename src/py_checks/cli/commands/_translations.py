"""The `translations` command: `stamp` a translation with its source's fingerprint."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from py_checks.config import find_root
from py_checks.core import EXIT_OK, EXIT_VIOLATION
from py_checks.translations import TranslationError, stamp

Paths = Annotated[
    list[Path],
    typer.Argument(help="the translations to stamp, under docs/langs/<lang>/"),
]

translations = typer.Typer(
    no_args_is_help=True,
    help="Translated documents: each one says which version of its source it was made from.",
)

console = Console(soft_wrap=True)
errors = Console(
    stderr=True,
    soft_wrap=True,
)


@translations.command("stamp")
def stamped(  # check-ok: keyword-only-arguments: typer parses the command's signature
    paths: Paths,
) -> None:
    """Write the fingerprint of each translation's source on its first line.

    Only the translations named, and only ones that exist: the translator
    writes the translation, then stamps it. `run --fix` never does this — a fix
    that rewrote the hash would bless a translation nobody updated.
    """
    root = find_root(start=Path.cwd())
    refused = 0
    for path in paths:
        try:
            translation = _within(
                root=root,
                path=path,
            )
            stamp(
                root=root,
                translation=translation,
            )
        except TranslationError as error:
            _say(
                console=errors,
                text=str(error),
            )
            refused += 1
            continue
        _say(
            console=console,
            text=f"stamped {translation}",
        )
    raise typer.Exit(EXIT_VIOLATION if refused else EXIT_OK)


def _within(
    *,
    root: Path,
    path: Path,
) -> str:
    """The path from the repository's root, the way the check names it."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as error:
        message = f"{path} lies outside the project at {root}"
        raise TranslationError(message) from error


def _say(
    *,
    console: Console,
    text: str,
) -> None:
    """Print as is: a line is a path, and brackets in it are not markup."""
    console.print(
        text,
        markup=False,
        highlight=False,
    )


def register(*, app: typer.Typer) -> None:
    app.add_typer(
        translations,
        name="translations",
    )
