"""The clock, the dice and a new identifier come through a port, not globally."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks._location import ZonedSettings, zoned
from py_checks.checks._names import matches
from py_checks.checks.effects._marker import MARKER
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.config import CheckSettings
    from py_checks.core import ParsedFile

CODE: Final = "determinism"


class DeterminismSettings(ZonedSettings):
    instead: dict[str, str] = {}  # noqa: RUF012 — pydantic copies the default value


class Determinism:
    """Fails if the code reads the clock, the dice or a new identifier itself.

    `datetime.now()`, `uuid4()` and `random.random()` make a use case
    untestable: the same input gives a different output, and the test either
    freezes the world with a mock or asserts nothing at all. Business code
    takes them as a dependency — `self._clock.now()`, an identifier handed out
    at the edge — and the rule leaves a call through a port alone: it judges
    global sources.

    Repositories are inside the same zone, and there the source is written in
    SQL: `func.gen_random_uuid()` inside an INSERT is the same decision one
    floor down, where it is even harder to see. A test has nothing to assert
    about it, the storage layer becomes the author of an identifier nobody
    passed it, and a uuid4 appears among uuid7s — random where everything else
    is ordered, and ordering is the whole reason an index on them is worth
    anything.

    A name is matched against the tail: `datetime.now` matches the spelling
    `datetime.datetime.now` too, and `random.*` matches any call into that
    module.

    Settings: `zones`, `instead`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = DeterminismSettings
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(
        cls,
        *,
        file: ParsedFile,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        limits = settings_as(
            settings=settings,
            model=DeterminismSettings,
            code=CODE,
        )
        where = zoned(
            file=file,
            zones=limits.zones,
        )
        if where is None or not limits.instead:
            return
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.Call):
                continue
            called = ast.unparse(node.func)
            said = cls._source(
                called=called,
                instead=limits.instead,
            )
            if said is None:
                continue
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                message=f"{called}() is not deterministic; {said}",
            )

    @staticmethod
    def _source(
        *,
        called: str,
        instead: dict[str, str],
    ) -> str | None:
        """Why such a call is banned, if it is in the table."""
        return next(
            (
                said
                for pattern, said in instead.items()
                if matches(
                    called=called,
                    pattern=pattern,
                )
            ),
            None,
        )
