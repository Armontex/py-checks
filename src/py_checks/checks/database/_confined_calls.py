"""A call that belongs to one module and to nobody else."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks._location import ZonedSettings, place
from py_checks.checks.database._marker import MARKER
from py_checks.config import CheckSettings
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.checks._location import Place
    from py_checks.core import ParsedFile

CODE: Final = "confined-calls"


class Confined(ZonedSettings):
    """Method names, the zone that bans them, and the module that owns them.

    `owner` is the module's name without the extension. The rule leaves it
    alone: that is where the call belongs, which is what makes it the owner.

    `skip` holds the pieces of the zone where the rule is silent. A method's
    name is all one file shows, and the broker's edge is the example: a
    consumer's `commit()` acknowledges an offset, not a database transaction.

    `because` is the reason in the refusal: it explains who owns this call,
    and it is printed to whoever wrote it in the wrong place.
    """

    methods: tuple[str, ...]
    skip: tuple[str, ...] = ()
    owner: str | None = None
    because: str = "another module owns this"


class ConfinedCallsSettings(CheckSettings):
    rules: tuple[Confined, ...] = ()


class ConfinedCalls:
    """Fails if a named method was called somewhere it does not belong.

    Written for the transaction boundary. A bet is one transaction: take the
    money, write the bet, write the event that tells the rest of the platform.
    A repository committing halfway turns it into three, and the balance stops
    agreeing with the bets. `begin` is banned next to `commit` and `rollback`
    for the same reason from the other end: the caller has already opened a
    transaction, and a second one inside either fails or quietly nests.

    A method's name is all one file shows: whose object it is would take type
    inference to say. That is why the rule is narrowed by a zone — one where
    `commit()` can only be the session's.

    Settings: `rules`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = ConfinedCallsSettings
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(
        cls,
        *,
        file: ParsedFile,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        rules = settings_as(
            settings=settings,
            model=ConfinedCallsSettings,
            code=CODE,
        ).rules
        where = place(file=file)
        if where is None:
            return
        listed = [
            rule
            for rule in rules
            if cls._covers(
                rule=rule,
                where=where,
                file=file,
            )
        ]
        if not listed:
            return
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            rule = next((one for one in listed if node.func.attr in one.methods), None)
            if rule is None:
                continue
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                message=f"{ast.unparse(node.func)}: {rule.because}",
            )

    @staticmethod
    def _covers(
        *,
        rule: Confined,
        where: Place,
        file: ParsedFile,
    ) -> bool:
        if rule.owner is not None and file.path.stem == rule.owner:
            return False
        if where.anywhere(zones=rule.skip):
            return False
        return where.anywhere(zones=rule.zones)
