"""The schema the migrations build, and the schema the models describe."""

from __future__ import annotations

import os
import subprocess  # noqa: S404 — calling alembic is what the rule is
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

# What alembic answers when there is nothing to add.
IN_STEP: Final = "No new upgrade operations detected"

# How a successful command exits; it has nothing to do with the library's own
# exit code.
DONE: Final = 0

DATABASE: Final = "drift.db"


class SchemaDriftSettings(CheckSettings):
    versions: Path = Path("migrations/versions")
    models: str = "src/*/infra/database/models"
    variable: str = "DATABASE_URL"
    url: str = "sqlite+aiosqlite:///{path}"
    alembic: tuple[str, ...] = ("alembic",)


class DriftError(RuntimeError):
    """The rule did not reach a verdict.

    An error of its own, so that "could not look" is never read as "nothing to
    look at": the rule's silence means there is no disagreement.
    """


class SchemaDrift:
    """Fails if the models and the migrations already describe different schemas.

    The model was changed, the revision was not written — and from there it
    all depends on where the code meets the schema. The tests, on their own
    database built from the metadata, are green; production was built by the
    migrations and knows nothing of the column the model already uses. The
    disagreement surfaces not in review but in the first query after the
    release.

    Static analysis cannot see it: one schema is written as declarations, the
    other as a history of changes, and only something that can run both can
    compare them. So the rule brings up an empty database of its own in a
    temporary directory, migrates it to `head` and asks `alembic check` what
    it would add itself. Its own, not the developer's database: that one
    stands at whatever revision it was left at — exactly the state the rule
    does not trust.

    A live database and a run of alembic are why the rule is declared
    `ENVIRONMENT`: it has no place in a commit hook. It is called in CI —
    `py-checks run --all` or `--select schema-drift`.

    Two caveats. The project's `env.py` must read the database address from an
    environment variable (`variable`): if it takes it from its own settings,
    the rule cannot slip an empty database underneath and will migrate
    whichever one it finds. The default address is SQLite, which needs
    `aiosqlite` installed; where it is missing, `url` holds the address of a
    throwaway CI database.

    Settings: `versions`, `models`, `variable`, `url`, `alembic`.
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
                        "the models describe a schema the migrations do not build",
                        found,
                        "write a revision: `alembic revision --autogenerate`, "
                        "then read what it writes",
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
        """What alembic would add to the history, or `None` when there is nothing to add."""
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
            raise DriftError(f"nowhere to keep the database: {unwritable}") from unwritable

    @classmethod
    def _migrated(
        cls,
        *,
        root: Path,
        url: str,
        limits: SchemaDriftSettings,
    ) -> None:
        """Bring an empty database up to `head`, or say why that failed."""
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
                        f"`alembic upgrade head` exited with {upgraded.returncode}",
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
        """alembic is called by the same name as in the caller's environment.

        The run is already inside the project's environment, and a second
        `uv run` inside it would rebuild that environment mid-check.
        """
        return subprocess.run(  # noqa: S603 — the argument list is built right here
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
        """The message's lines without empty ones: a silent alembic must not add one."""
        return "\n".join(line for line in lines if line)

    @staticmethod
    def _violation(
        *,
        root: Path,
        limits: SchemaDriftSettings,
        message: str,
    ) -> Violation:
        """The violation points at the revisions folder: the fix, a new revision, goes there."""
        return Violation(
            path=root / limits.versions,
            line=1,
            column=1,
            code=CODE,
            message=message,
        )
