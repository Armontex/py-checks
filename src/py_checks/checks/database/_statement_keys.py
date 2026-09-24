"""A statement names a column by attribute, not by string, and goes to the database once."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks._location import ZonedSettings, zoned
from py_checks.checks._names import name
from py_checks.checks.database._marker import MARKER
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.config import CheckSettings
    from py_checks.core import ParsedFile

CODE: Final = "statement-keys"

SAID: Final = "names a column by string; a mapped attribute moves with the column"


class StatementKeysSettings(ZonedSettings):
    lists: tuple[str, ...] = ("index_elements",)
    mappings: tuple[str, ...] = ("set_",)
    sub_queries: tuple[str, ...] = ("from_select",)
    loops: tuple[str, ...] = ("execute",)


class StatementKeys:
    """Fails if a statement names a column by string, or goes to the database in a loop.

    Rows are assembled through models, so pyright holds the column list: a
    missing column is a missing argument, a renamed one an unexpected keyword.
    A string key in `index_elements=[...]`, `set_={...}` or `from_select`
    opens the hole again: it matches nothing at check time, and either fails
    or quietly stops matching on the row that runs.

    `index_elements` and `set_` together are `ON CONFLICT DO UPDATE` — that
    is the inbox and every upsert. A string that has stopped matching there
    raises nothing: the conflict is simply not found, the duplicate is
    inserted a second time, and idempotency — the whole reason the inbox
    exists — quietly ends.

    The second rule: an `execute(...)` inside a loop is a trip to the database
    per iteration, the N+1 shape. A hundred bets is a hundred round trips where
    one statement over the whole set would have done. Sometimes the loop is
    honest — three constants, and no single statement says the same thing —
    so the rule is lifted by a mark on the line of the loop or of the call,
    rather than left out.

    Settings: `zones`, `lists`, `mappings`, `sub-queries`, `loops`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = StatementKeysSettings
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
            model=StatementKeysSettings,
            code=CODE,
        )
        where = zoned(
            file=file,
            zones=limits.zones,
        )
        if where is None:
            return
        for node in ast.walk(file.tree):
            if isinstance(node, ast.Call):
                yield from cls._keys(
                    file=file,
                    node=node,
                    limits=limits,
                )
            if isinstance(node, ast.For | ast.AsyncFor | ast.While):
                yield from cls._loop(
                    file=file,
                    node=node,
                    limits=limits,
                )

    @classmethod
    def _keys(
        cls,
        *,
        file: ParsedFile,
        node: ast.Call,
        limits: StatementKeysSettings,
    ) -> Iterator[Violation]:
        for keyword in node.keywords:
            if keyword.arg in limits.lists:
                yield from cls._strings(
                    file=file,
                    written=keyword.arg,
                    nodes=cls._elements(node=keyword.value),
                )
            if keyword.arg in limits.mappings:
                yield from cls._strings(
                    file=file,
                    written=keyword.arg,
                    nodes=cls._keyed(node=keyword.value),
                )
        if name(node=node.func) in limits.sub_queries and node.args:
            yield from cls._strings(
                file=file,
                written=name(node=node.func),
                nodes=cls._elements(node=node.args[0]),
            )

    @staticmethod
    def _loop(
        *,
        file: ParsedFile,
        node: ast.For | ast.AsyncFor | ast.While,
        limits: StatementKeysSettings,
    ) -> Iterator[Violation]:
        """A trip to the database on every iteration."""
        for child in ast.walk(node):
            if not isinstance(child, ast.Call) or name(node=child.func) not in limits.loops:
                continue
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                # The mark is lifted from the line of the loop or from any line of
                # the call: the reason belongs wherever its author writes it.
                end_line=child.end_lineno or child.lineno,
                message=(
                    f"{name(node=child.func)}() inside a loop is a trip to the database per "
                    f"iteration; one statement over the whole set says the same thing"
                ),
            )

    @staticmethod
    def _strings(
        *,
        file: ParsedFile,
        written: str,
        nodes: Iterator[ast.expr],
    ) -> Iterator[Violation]:
        for node in nodes:
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                message=f"{written}: {SAID}",
            )

    @staticmethod
    def _elements(*, node: ast.expr) -> Iterator[ast.expr]:
        if isinstance(node, ast.List | ast.Tuple | ast.Set):
            yield from node.elts

    @staticmethod
    def _keyed(*, node: ast.expr) -> Iterator[ast.expr]:
        if isinstance(node, ast.Dict):
            yield from (key for key in node.keys if key is not None)
