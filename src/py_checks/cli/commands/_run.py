"""The `run` command: run the checks."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

from py_checks.config import Config, find_root, load
from py_checks.core import (
    Checks,
    Scope,
    UnknownCheckError,
    Violation,
    available,
    fix,
    get,
    python_files,
    reformat,
    report,
    survey,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from py_checks.core import Check


def run(  # check-ok: keyword-only-arguments: typer parses the command's signature
    paths: Annotated[
        list[Path] | None,
        typer.Argument(help="files or directories; without them, the whole of the project's `src`"),
    ] = None,
    select: Annotated[
        list[str] | None,
        typer.Option(
            "--select",
            "-s",
            help="check codes, comma-separated; without them, every enabled one",
        ),
    ] = None,
    autofix: Annotated[
        bool,
        typer.Option("--fix", help="repair what repairs itself"),
    ] = False,
    everything: Annotated[
        bool,
        typer.Option("--all", help="including the rules that need a live environment"),
    ] = False,
) -> None:
    """Check the files and return an exit code: 0 — clean, 1 — violations found."""
    root = find_root(start=Path.cwd())
    config = load(root=root)
    chosen = _chosen(
        select=select,
        config=config,
        paths=bool(paths),
        everything=everything,
    )
    # Only file rules need the tree walked: a run of one project rule should not
    # read a list of a thousand files only to hand it to nobody.
    files = (
        python_files(
            paths=paths or [],
            root=root,
            default=root / config.src,
            exclude=config.excluded,
        )
        if chosen.files
        else []
    )
    violations = survey(
        chosen=chosen,
        files=files,
        config=config,
        root=root,
    )
    if autofix:
        violations = _fixed(violations=violations)
    raise typer.Exit(
        report(
            violations=violations,
            root=root,
            checked=len(files),
        )
    )


def _fixed(*, violations: list[Violation]) -> list[Violation]:
    """Apply the fixes and return what is left for a person."""
    changed, left = fix(violations=violations)
    reformat(paths=changed)
    return left


def _chosen(
    *,
    select: list[str] | None,
    config: Config,
    paths: bool,
    everything: bool,
) -> Checks:
    """The selected checks, or, with no selection, all but those disabled in config.

    An explicit `--select` beats everything else: a check called by name is
    wanted right now — despite `ignore`, and despite needing a database.
    """
    listed = available()
    if select:
        return listed.only(codes=_codes(select=select))
    return listed.only(
        codes={
            code
            for code, check in listed.listed.items()
            if config.enabled(code=code)
            and _wanted(
                check=check,
                paths=paths,
                everything=everything,
            )
        }
    )


def _codes(*, select: Sequence[str]) -> set[str]:
    """The codes from `--select`: a repeated flag and a comma-separated list.

    A set of rules is written on one line — `-s raw-sql,statement-keys` —
    because that is how it is held in the head: as a list, not a flag per rule.
    A repeated flag still works; both ways give the same thing.

    A typo in a code is an argument parse error, not a crash: the check's name
    comes from the command line, and answering it with a traceback shows the
    internals where it was a person who made the mistake.
    """
    named = (code.strip() for value in select for code in value.split(","))
    try:
        return {get(code=code).code for code in named if code}
    except UnknownCheckError as error:
        raise typer.BadParameter(str(error), param_hint="--select") from error


def _wanted(
    *,
    check: Check,
    paths: bool,
    everything: bool,
) -> bool:
    """Whether a rule belongs in a run that named no codes.

    Named paths do not concern the project rules: a run over one file checks
    that file, not the project around it. A rule that needs a live environment
    belongs in CI, not in a commit hook — it is called with `--all` or by
    name.
    """
    if paths and check.scope is not Scope.FILE:
        return False
    if check.scope is Scope.ENVIRONMENT:
        return everything
    return True


def register(*, app: typer.Typer) -> None:
    app.command("run")(run)
