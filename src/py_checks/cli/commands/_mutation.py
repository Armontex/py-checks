"""Команда `mutation`: мутационный гейт — `diff`, `full` и `record`."""

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
        help="сколько мутантов проверять разом; по умолчанию — из настроек или решает mutmut",
    ),
]

Against = Annotated[
    str | None,
    typer.Option(
        "--against",
        help="с чем сравнивать ветку; по умолчанию — что заменяет пуш, иначе develop",
    ),
]

mutation = typer.Typer(
    no_args_is_help=True,
    help="Мутационный гейт: пуш не оставляет строки, поломку которой не заметит ни один тест.",
)

console = Console(soft_wrap=True)
errors = Console(
    stderr=True,
    soft_wrap=True,
)


@mutation.command("diff")
def diff(  # check-ok: keyword-only-arguments: подпись команды разбирает typer
    children: Children = None,
    against: Against = None,
) -> None:
    """Только модули, которые тронула ветка, — то, что гоняет пуш."""
    project = _project(children=children)
    try:
        diffed = project.diff(against=against)
    except GateError as error:
        _refuse(message=str(error))
    if diffed is None:
        errors.print("[yellow]сравнить не с чем — ни пуша, ни develop; гоню всё[/yellow]")
        full(children=children)
        return
    verdict = diffed.verdict
    if not verdict.counted:
        _say(text=f"ok: против {diffed.against} мутируемое не менялось")
        raise typer.Exit(EXIT_OK)
    _counted(
        tally=verdict.tally,
        where=" в изменённых модулях",
    )
    _judged(verdict=verdict)
    _say(
        text=(
            f"ok: {verdict.total} выживш(их) в {len(verdict.counted)} "
            f"изменённ(ых) модул(ях) против {diffed.against}"
        )
    )


@mutation.command("full")
def full(  # check-ok: keyword-only-arguments: подпись команды разбирает typer
    children: Children = None,
) -> None:
    """Всё, что мутируется, против записи — модуль за модулем."""
    project = _project(children=children)
    verdict = _full(project=project)
    _counted(tally=verdict.tally)
    _judged(verdict=verdict)
    before = sum(verdict.recorded.values())
    if verdict.total < before:
        _say(
            text=(
                f"ok: {verdict.total} выживш(их), по записи {before}. "
                f"Запусти `py-checks mutation record`, чтобы запись не носила отвоёванное"
            )
        )
        return
    _say(text=f"ok: {verdict.total} выживш(их), как в записи")


@mutation.command("record")
def record(  # check-ok: keyword-only-arguments: подпись команды разбирает typer
    children: Children = None,
) -> None:
    """Полный прогон, и его итог по модулям — в файл записи."""
    project = _project(children=children)
    try:
        counted = project.record()
    except GateError as error:
        _refuse(message=str(error))
    _say(
        text=(
            f"записан {project.baseline.relative_to(project.root)}: "
            f"{sum(counted.values())} выживш(их) в {len(counted)} модул(ях)"
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
    """Сколько мутантов прогон попробовал и чем кончилось, — справка, не суд."""
    other = f", прочее {tally.other}" if tally.other else ""
    _say(
        text=(
            f"мутантов{where}: запущено {tally.tried}, убито {tally.killed}, "
            f"осталось {tally.alive}{other}"
        )
    )


def _judged(*, verdict: Verdict) -> None:
    """Отказ, если где-то выживших больше записанного; иначе — ничего."""
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
            "Строку, которую ты тронул, можно сломать, и ни один тест этого не заметит.\n"
            "Убей мутанта тестом — или запусти `py-checks mutation record`, если выживший "
            "не стоит теста, и скажи в коммите почему."
        )
    )


def _survivors(*, alive: list[str]) -> Table:
    """Кто выжил, модуль за модулем: читателю нужно, где дыра, а номер мутанта —
    когда он пойдёт её закрывать."""
    table = Table(
        title="выжившие мутанты",
        title_style="bold",
        header_style="bold",
    )
    table.add_column(
        "модуль",
        overflow="fold",
    )
    table.add_column(
        "мутант",
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
        title="больше, чем записано",
        title_style="bold",
        header_style="bold",
    )
    table.add_column(
        "модуль",
        overflow="fold",
    )
    table.add_column(
        "выжило",
        justify="right",
    )
    table.add_column(
        "по записи",
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
    """Сказать, что делать, и выйти с кодом, который читает оболочка."""
    errors.print(
        Panel(
            message,
            border_style="red",
            title="мутационный гейт",
        )
    )
    raise typer.Exit(EXIT_VIOLATION)


def _say(*, text: str) -> None:
    """Печатать как есть: в строке бывают пути и имена модулей."""
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
