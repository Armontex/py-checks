"""SQL written as a string where an expression would do."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks._names import name
from py_checks.checks.database._marker import MARKER
from py_checks.config import CheckSettings
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.core import ParsedFile

CODE: Final = "raw-sql"

# The call, and what is written instead of the string. Each takes the SQL as
# its first positional argument.
CALLS: Final[dict[str, str]] = {
    "CheckConstraint": "a column expression, e.g. and_(margin >= NOTHING, margin < WHOLE)",
    "text": "select()/insert() built from the model's attributes",
    "literal_column": "the mapped column itself",
    "column": "the mapped column itself",
}


class RawSqlSettings(CheckSettings):
    instead: dict[str, str] = CALLS


class RawSql:
    """Fails if SQL is written as a string where an expression would do.

    A CHECK written as `"margin >= 0 AND margin < 1"` is a second definition
    of a rule the domain has already stated, in a language nobody in the
    repository checks. Rename the column and the string still compiles; move
    the bound and the string still names the old number, and the disagreement
    surfaces as a constraint violation on a row that was correct by every rule
    the code knew.

    Written as an expression — `CheckConstraint(and_(margin >= NOTHING, margin
    < WHOLE))` — it is made of an attribute pyright already checks and of the
    constants the entity refuses by, so there is nowhere for them to drift
    apart.

    The same goes for `text()`, `literal_column()` and `column()`: a query
    built as a string is a query nobody checks, and one built from a value
    that came from anywhere is an injection waiting for a forgetful caller.

    Where there honestly is no expression — `SELECT 1` for a liveness probe,
    reading alembic's own table — the reason goes on the line:
    `# db-ok: raw-sql: a liveness probe has no ORM form`. The mark is lifted
    from any line of the call itself and reaches no further: a mark on the
    enclosing statement excuses that statement, not the SQL inside.

    Migrations are outside the rule's jurisdiction: a migration is history, it
    may have no right to import those very constants, so its SQL is written
    out in words and frozen on the day it was born. That is the project's
    `exclude`, not the rule's business.

    Settings: `instead`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = RawSqlSettings
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(
        cls,
        *,
        file: ParsedFile,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        instead = settings_as(
            settings=settings,
            model=RawSqlSettings,
            code=CODE,
        ).instead
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            written = name(node=node.func)
            if written not in instead or not cls._sql(node=node.args[0]):
                continue
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                # The mark is lifted from any line of the call itself.
                end_line=node.end_lineno or node.lineno,
                message=f"{written}(...) with an SQL string; instead: {instead[written]}",
            )

    @staticmethod
    def _sql(*, node: ast.expr) -> bool:
        """A string literal, or a string built from literals."""
        match node:
            case ast.Constant(value=str()):
                return True
            case ast.JoinedStr() | ast.BinOp(op=ast.Add() | ast.Mod()):
                return any(
                    isinstance(part, ast.Constant) and isinstance(part.value, str)
                    for part in ast.walk(node)
                )
            case _:
                return False
