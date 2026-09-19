"""Схема, которую строят миграции, и схема, которую описывают модели."""

from __future__ import annotations

import os
import subprocess  # noqa: S404 — правило состоит в том, чтобы позвать alembic
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks.database._marker import MARKER
from py_checks.config import CheckSettings
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator, Sequence

CODE: Final = "schema-drift"

# Чем alembic отвечает, когда дописывать нечего.
IN_STEP: Final = "No new upgrade operations detected"

# Так выходит удавшаяся команда; к коду выхода самой библиотеки это отношения
# не имеет.
DONE: Final = 0

DATABASE: Final = "drift.db"


class SchemaDriftSettings(CheckSettings):
    versions: Path = Path("migrations/versions")
    models: str = "src/*/infra/database/models"
    variable: str = "DATABASE_URL"
    url: str = "sqlite+aiosqlite:///{path}"
    alembic: tuple[str, ...] = ("alembic",)


class DriftError(RuntimeError):
    """Правило не дошло до вердикта.

    Своя ошибка, чтобы «не удалось посмотреть» никогда не читалось как
    «смотреть не на что»: молчание правила означает, что расхождения нет.
    """


class SchemaDrift:
    """Падает, если модели и миграции описывают уже разные схемы.

    Модель поменяли, ревизию не написали — и дальше всё зависит от того, где
    код встретится со схемой. Тесты на своей базе, поднятой из метаданных,
    зелены; прод поднят миграциями и не знает о колонке, которой модель уже
    пользуется. Расхождение всплывает не в ревью, а в первом запросе после
    выкатки.

    Статикой это не видно: одна схема написана декларациями, вторая — историей
    правок, и сравнивает их только тот, кто умеет обе выполнить. Поэтому
    правило поднимает свою пустую базу во временной директории, накатывает её
    до `head` и спрашивает `alembic check`, что он дописал бы сам. Своя, а не
    база разработчика: та стоит на ревизии, на которой её оставили, — ровно то
    состояние, которому правило и не верит.

    Живая база и запуск alembic — причина, по которой правило объявлено
    `ENVIRONMENT`: в хуке на коммит ему не место. Его зовут в CI —
    `py-checks run --all` или `--select schema-drift`.

    Две оговорки. `env.py` проекта обязан читать адрес базы из переменной
    окружения (`variable`): если он берёт его из своих настроек, правило
    подсунуть пустую базу не может и накатит миграции на ту, что найдёт.
    Адрес по умолчанию — SQLite, а ему нужен установленный `aiosqlite`; где
    его нет, в `url` пишут адрес одноразовой базы CI.

    Настройки: `versions`, `models`, `variable`, `url`, `alembic`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = SchemaDriftSettings
    scope: ClassVar[Scope] = Scope.ENVIRONMENT
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(
        cls,
        *,
        root: Path,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        limits = settings_as(
            settings=settings,
            model=SchemaDriftSettings,
            code=CODE,
        )
        revisions = cls._revisions(
            root=root,
            limits=limits,
        )
        models = cls._models(
            root=root,
            limits=limits,
        )
        if not revisions and not models:
            return
        try:
            found = cls._compared(
                root=root,
                limits=limits,
            )
        except DriftError as broken:
            yield cls._violation(
                root=root,
                limits=limits,
                message=str(broken),
            )
            return
        if found is not None:
            yield cls._violation(
                root=root,
                limits=limits,
                message=cls._joined(
                    lines=(
                        "модели описывают схему, которую миграции не строят",
                        found,
                        "напиши ревизию: `alembic revision --autogenerate`, "
                        "потом прочитай, что она пишет",
                    ),
                ),
            )

    @classmethod
    def _compared(
        cls,
        *,
        root: Path,
        limits: SchemaDriftSettings,
    ) -> str | None:
        """Что alembic дописал бы к истории, или `None`, когда дописывать нечего."""
        with cls._database() as path:
            url = limits.url.format(path=path)
            cls._migrated(
                root=root,
                url=url,
                limits=limits,
            )
            return cls._behind(
                root=root,
                url=url,
                limits=limits,
            )

    @staticmethod
    def _revisions(
        *,
        root: Path,
        limits: SchemaDriftSettings,
    ) -> Sequence[Path]:
        versions = root / limits.versions
        if not versions.is_dir():
            return ()
        return sorted(path for path in versions.rglob("*.py") if path.name != "__init__.py")

    @staticmethod
    def _models(
        *,
        root: Path,
        limits: SchemaDriftSettings,
    ) -> Sequence[Path]:
        return sorted(
            path
            for directory in root.glob(limits.models)
            for path in directory.rglob("*.py")
            if path.name != "__init__.py"
        )

    @staticmethod
    @contextmanager
    def _database() -> Generator[Path]:
        try:
            with tempfile.TemporaryDirectory() as directory:
                yield Path(directory) / DATABASE
        except OSError as unwritable:
            raise DriftError(f"негде держать базу: {unwritable}") from unwritable

    @classmethod
    def _migrated(
        cls,
        *,
        root: Path,
        url: str,
        limits: SchemaDriftSettings,
    ) -> None:
        """Поднять пустую базу до `head` или сказать, почему не вышло."""
        upgraded = cls._finished(
            command=(*limits.alembic, "upgrade", "head"),
            root=root,
            url=url,
            limits=limits,
        )
        if upgraded.returncode != DONE:
            raise DriftError(
                cls._joined(
                    lines=(
                        f"`alembic upgrade head` вышел с {upgraded.returncode}",
                        cls._said(finished=upgraded),
                    ),
                )
            )

    @classmethod
    def _behind(
        cls,
        *,
        root: Path,
        url: str,
        limits: SchemaDriftSettings,
    ) -> str | None:
        checked = cls._finished(
            command=(*limits.alembic, "check"),
            root=root,
            url=url,
            limits=limits,
        )
        if checked.returncode == DONE or IN_STEP in checked.stdout:
            return None
        return cls._said(finished=checked)

    @staticmethod
    def _finished(
        *,
        command: tuple[str, ...],
        root: Path,
        url: str,
        limits: SchemaDriftSettings,
    ) -> subprocess.CompletedProcess[str]:
        """alembic зовётся тем же именем, что и в окружении вызвавшего.

        Прогон уже идёт из окружения проекта, и второй `uv run` внутри него
        пересобрал бы это окружение посреди проверки.
        """
        return subprocess.run(  # noqa: S603 — список аргументов собран здесь же
            command,
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            env=os.environ | {limits.variable: url},
        )

    @staticmethod
    def _said(*, finished: subprocess.CompletedProcess[str]) -> str:
        return finished.stderr.strip() or finished.stdout.strip()

    @staticmethod
    def _joined(*, lines: tuple[str, ...]) -> str:
        """Строки сообщения без пустых: молчаливый alembic не должен добавлять пустую."""
        return "\n".join(line for line in lines if line)

    @staticmethod
    def _violation(
        *,
        root: Path,
        limits: SchemaDriftSettings,
        message: str,
    ) -> Violation:
        """Нарушение указывает на папку ревизий: там же и починка — новой ревизией."""
        return Violation(
            path=root / limits.versions,
            line=1,
            column=1,
            code=CODE,
            message=message,
        )
