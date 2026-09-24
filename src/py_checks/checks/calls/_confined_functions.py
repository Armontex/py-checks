"""Some functions have exactly as many lawful call sites as are listed."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks._location import place
from py_checks.checks._names import matches
from py_checks.checks.calls._marker import MARKER
from py_checks.config import CheckSettings
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.core import ParsedFile

CODE: Final = "confined-functions"


class ConfinedFunctionsSettings(CheckSettings):
    calls: dict[str, tuple[str, ...]] = {}  # noqa: RUF012 — pydantic copies the value itself
    declared_in: str | None = None


class ConfinedFunctions:
    """Fails if a named function is called from somewhere it may not be.

    Written for money conversion. A service counts in one currency, and the
    guarantee behind that sentence is not the name of a type: it is that
    conversion has one implementation and its call sites can be listed.
    Anywhere else, a conversion is an amount in somebody's currency in the
    middle of a calculation, and the error it gives is a number that is right
    up to the day two currencies meet.

    A place is a piece of a path, not a file: an edge is a place in the design,
    and a file split in two has not stopped being an edge.

    `declared-in` is the module where the function is declared: there it is
    written, not called, and the rule leaves it alone.

    Settings: `calls`, `declared-in`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = ConfinedFunctionsSettings
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
            model=ConfinedFunctionsSettings,
            code=CODE,
        )
        where = place(file=file)
        if where is None or not limits.calls:
            return
        if limits.declared_in is not None and where.holds(path=limits.declared_in):
            return
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.Call):
                continue
            called = ast.unparse(node.func)
            allowed = cls._allowed(
                called=called,
                calls=limits.calls,
            )
            if allowed is None or where.anywhere(
                zones=allowed,
            ):
                continue
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                message=f"{called}() is not called from here; its places are {', '.join(allowed)}",
            )

    @staticmethod
    def _allowed(
        *,
        called: str,
        calls: dict[str, tuple[str, ...]],
    ) -> tuple[str, ...] | None:
        return next(
            (
                zones
                for pattern, zones in calls.items()
                if matches(
                    called=called,
                    pattern=pattern,
                )
            ),
            None,
        )
