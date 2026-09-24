"""The `mutation` command: the mutation gate — `diff`, `full` and `record`."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated, NoReturn

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from py_checks.config import find_root, load
from py_checks.core import EXIT_OK, EXIT_VIOLATION
from py_checks.mutation import GateError, gate

if TYPE_CHECKING:
    from py_checks.mutation import Gate, Tally, Verdict

Children = Annotated[
    int | None,
    typer.Option(
        "--children",
        min=1,
        help="how many mutants to run at once; by default from the settings, or mutmut decides",
    ),
]

Against = Annotated[
    str | None,
    typer.Option(
        "--against",
        help="what to compare the branch to; by default what the push replaces, otherwise develop",
    ),
]

mutation = typer.Typer(
    no_args_is_help=True,
    help="The mutation gate: a push leaves no line whose breakage no test would notice.",
)

console = Console(soft_wrap=True)
errors = Console(
    stderr=True,
    soft_wrap=True,
)


@mutation.command("diff")
def diff(  # check-ok: keyword-only-arguments: typer parses the command's signature
    children: Children = None,
    against: Against = None,
) -> None:
    """Only the modules the branch touched — what a push runs."""
    project = _project(children=children)
    try:
        diffed = project.diff(against=against)
    except GateError as error:
        _refuse(message=str(error))
    if diffed is None:
        errors.print("[yellow]nothing to compare to — no push, no develop; running all[/yellow]")
        full(children=children)
        return
    verdict = diffed.verdict
    if not verdict.counted:
        _say(text=f"ok: nothing mutable changed against {diffed.against}")
        raise typer.Exit(EXIT_OK)
    _counted(
        tally=verdict.tally,
        where=" in changed modules",
    )
    _judged(verdict=verdict)
    _say(
        text=(
            f"ok: {verdict.total} survivor(s) in {len(verdict.counted)} "
            f"changed module(s) against {diffed.against}"
        )
    )


@mutation.command("full")
def full(  # check-ok: keyword-only-arguments: typer parses the command's signature
    children: Children = None,
) -> None:
    """Everything that is mutated, against the record — module by module."""
    project = _project(children=children)
    verdict = _full(project=project)
    _counted(tally=verdict.tally)
    _judged(verdict=verdict)
    before = sum(verdict.recorded.values())
    if verdict.total < before:
        _say(
            text=(
                f"ok: {verdict.total} survivor(s), {before} on record. "
                f"Run `py-checks mutation record` so the record stops carrying what was won back"
            )
        )
        return
    _say(text=f"ok: {verdict.total} survivor(s), as recorded")


@mutation.command("record")
def record(  # check-ok: keyword-only-arguments: typer parses the command's signature
    children: Children = None,
) -> None:
    """A full pass, with its result per module written to the record file."""
    project = _project(children=children)
    try:
        counted = project.record()
    except GateError as error:
        _refuse(message=str(error))
    _say(
        text=(
            f"recorded {project.baseline.relative_to(project.root)}: "
            f"{sum(counted.values())} survivor(s) in {len(counted)} module(s)"
        )
    )


def _project(*, children: int | None) -> Gate:
    root = find_root(start=Path.cwd())
    return gate(
        root=root,
        config=load(root=root),
        children=children,
    )


def _full(*, project: Gate) -> Verdict:
    try:
        return project.full()
    except GateError as error:
        _refuse(message=str(error))


def _counted(
    *,
    tally: Tally,
    where: str = "",
) -> None:
    """How many mutants the pass tried and how it ended — information, not a verdict."""
    other = f", other {tally.other}" if tally.other else ""
    _say(
        text=(
            f"mutants{where}: run {tally.tried}, killed {tally.killed}, left {tally.alive}{other}"
        )
    )


def _judged(*, verdict: Verdict) -> None:
    """A refusal if some module has more survivors than recorded; otherwise nothing."""
    grown = verdict.grown
    if not grown:
        return
    errors.print(
        _survivors(
            alive=[mutant for mutant in verdict.alive if mutant.rpartition(".")[0] in grown],
        )
    )
    errors.print(_growth(grown=grown))
    _refuse(
        message=(
            "A line you touched can be broken and no test will notice.\n"
            "Kill the mutant with a test — or run `py-checks mutation record` if the survivor "
            "is not worth a test, and say why in the commit."
        )
    )


def _survivors(*, alive: list[str]) -> Table:
    """Who survived, module by module: the reader needs where the hole is, and the
    mutant's number once they go to close it."""
    table = Table(
        title="surviving mutants",
        title_style="bold",
        header_style="bold",
    )
    table.add_column(
        "module",
        overflow="fold",
    )
    table.add_column(
        "mutant",
        overflow="fold",
    )
    for mutant in sorted(alive):
        module, _, name = mutant.rpartition(".")
        table.add_row(
            module,
            name,
        )
    return table


def _growth(*, grown: dict[str, tuple[int, int]]) -> Table:
    table = Table(
        title="more than recorded",
        title_style="bold",
        header_style="bold",
    )
    table.add_column(
        "module",
        overflow="fold",
    )
    table.add_column(
        "survived",
        justify="right",
    )
    table.add_column(
        "on record",
        justify="right",
    )
    for module, (now, before) in grown.items():
        table.add_row(
            module,
            f"[red]{now}[/red]",
            str(before),
        )
    return table


def _refuse(*, message: str) -> NoReturn:
    """Say what to do and exit with a code the shell reads."""
    errors.print(
        Panel(
            message,
            border_style="red",
            title="mutation gate",
        )
    )
    raise typer.Exit(EXIT_VIOLATION)


def _say(*, text: str) -> None:
    """Print as is: a line may hold paths and module names."""
    console.print(
        text,
        markup=False,
        highlight=False,
    )


def register(*, app: typer.Typer) -> None:
    app.add_typer(
        mutation,
        name="mutation",
    )
