"""Команда `drift`: модели и миграции описывают одну и ту же схему."""

from __future__ import annotations

import os
import subprocess  # noqa: S404 — команда запускает alembic, в этом она и состоит
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Final

import typer
from rich.console import Console

from python_checks.config import CheckSettings, find_root, load
from python_checks.core import EXIT_OK, EXIT_VIOLATION

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

CODE: Final = "drift"

IN_STEP: Final = "No new upgrade operations detected"
DATABASE: Final = "drift.db"


class DriftSettings(CheckSettings):
    """Где лежат миграции и модели и чем поднимается пустая база.

    `alembic` зовётся тем же именем, что и в окружении вызвавшего: команда уже
    запущена из окружения проекта, и второй `uv run` внутри неё пересобрал бы
    его посреди проверки.
    """

    versions: Path = Path("migrations/versions")
    models: str = "src/*/infra/database/models"
    variable: str = "DATABASE_URL"
    url: str = "sqlite+aiosqlite:///{path}"
    alembic: tuple[str, ...] = ("alembic",)


class DriftError(RuntimeError):
    """Проверка не дошла до вердикта.

    Своя ошибка, чтобы «не удалось посмотреть» никогда не читалось как
    «смотреть не на что»: пустой отчёт означает, что расхождения нет.
    """


def drift() -> None:
    """Накатить пустую базу до `head` и спросить alembic, чего не хватает."""
    root = find_root(start=Path.cwd())
    console = Console(
        stderr=True,
        soft_wrap=True,
    )
    limits = _settings(root=root)
    revisions = _revisions(
        root=root,
        limits=limits,
    )
    models = _models(
        root=root,
        limits=limits,
    )
    if not revisions and not models:
        _say(
            text="ok: ни моделей, ни ревизий — расходиться нечему",
            console=console,
        )
        raise typer.Exit(EXIT_OK)
    try:
        with _database() as path:
            url = limits.url.format(path=path)
            _migrated(
                root=root,
                url=url,
                limits=limits,
            )
            found = _behind(
                root=root,
                url=url,
                limits=limits,
            )
    except DriftError as broken:
        _say(
            text=f"{CODE}: {broken}",
            console=console,
        )
        raise typer.Exit(EXIT_VIOLATION) from broken
    if found is not None:
        _say(
            text=(
                f"{CODE}: модели описывают схему, которую миграции не строят\n{found}\n"
                f"напиши ревизию: `alembic revision --autogenerate`, потом прочитай, что она пишет"
            ),
            console=console,
        )
        raise typer.Exit(EXIT_VIOLATION)
    _say(
        text=f"ok: {len(models)} модулей моделей и {len(revisions)} ревизий описывают одну схему",
        console=console,
    )
    raise typer.Exit(EXIT_OK)


def _settings(*, root: Path) -> DriftSettings:
    settings = load(root=root).settings_for(
        code=CODE,
        model=DriftSettings,
    )
    if not isinstance(settings, DriftSettings):  # pragma: no cover — модель задаёт сам вызов
        raise DriftError(f"[tool.python-checks.{CODE}]: не те настройки")
    return settings


def _revisions(
    *,
    root: Path,
    limits: DriftSettings,
) -> Sequence[Path]:
    versions = root / limits.versions
    if not versions.is_dir():
        return ()
    return sorted(path for path in versions.rglob("*.py") if path.name != "__init__.py")


def _models(
    *,
    root: Path,
    limits: DriftSettings,
) -> Sequence[Path]:
    return sorted(
        path
        for directory in root.glob(limits.models)
        for path in directory.rglob("*.py")
        if path.name != "__init__.py"
    )


@contextmanager
def _database() -> Generator[Path]:
    """Пустая база этой команды, удаляемая следом.

    Своя, а не разработчика: та стоит на той ревизии, на которой её оставили, —
    ровно то состояние, которому эта проверка и не верит.
    """
    try:
        with tempfile.TemporaryDirectory() as directory:
            yield Path(directory) / DATABASE
    except OSError as unwritable:
        raise DriftError(f"негде держать базу: {unwritable}") from unwritable


def _migrated(
    *,
    root: Path,
    url: str,
    limits: DriftSettings,
) -> None:
    """Поднять пустую базу до `head` или сказать, почему не вышло."""
    upgraded = _finished(
        command=(*limits.alembic, "upgrade", "head"),
        root=root,
        url=url,
        limits=limits,
    )
    if upgraded.returncode != EXIT_OK:
        said = _said(finished=upgraded)
        raise DriftError(f"`alembic upgrade head` вышел с {upgraded.returncode}\n{said}")


def _behind(
    *,
    root: Path,
    url: str,
    limits: DriftSettings,
) -> str | None:
    """Что alembic написал бы сам, или None, когда писать нечего."""
    checked = _finished(
        command=(*limits.alembic, "check"),
        root=root,
        url=url,
        limits=limits,
    )
    if checked.returncode == EXIT_OK or IN_STEP in checked.stdout:
        return None
    return _said(finished=checked)


def _finished(
    *,
    command: tuple[str, ...],
    root: Path,
    url: str,
    limits: DriftSettings,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 — список аргументов собран здесь же
        command,
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        env=os.environ | {limits.variable: url},
    )


def _said(*, finished: subprocess.CompletedProcess[str]) -> str:
    return finished.stderr.strip() or finished.stdout.strip()


def _say(
    *,
    text: str,
    console: Console,
) -> None:
    console.print(
        text,
        markup=False,
        highlight=False,
    )


def register(*, app: typer.Typer) -> None:
    app.command(CODE)(drift)
