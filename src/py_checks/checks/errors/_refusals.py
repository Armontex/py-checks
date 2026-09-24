"""A refusal the caller has no way to answer is not a refusal but a crash."""

from __future__ import annotations

import ast
import builtins
from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks._location import ZonedSettings, zoned
from py_checks.checks._names import name
from py_checks.checks.errors._marker import MARKER
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.config import CheckSettings
    from py_checks.core import ParsedFile

CODE: Final = "refusals"

# The exceptions the interpreter itself ships, by name. Read from `builtins`
# rather than listed: somebody would have to maintain the list, and it changes
# from one version of the language to the next.
BUILTINS: Final[frozenset[str]] = frozenset(
    found
    for found, value in vars(builtins).items()
    if isinstance(value, type) and issubclass(value, BaseException)
)


class RefusalsSettings(ZonedSettings):
    """Where to judge, what carries the code, and what is not a refusal.

    With `carries` unset the project has no refusal code of its own, and the
    rule judges only builtin exceptions: they carry no code in any form. With
    it set, an error of your own must carry it, except those in `internal`.
    """

    carries: str | None = None
    allow: tuple[str, ...] = ()
    internal: tuple[str, ...] = ()


class Refusals:
    """Fails when a refusal leaves without a code anyone can branch on.

    A refusal has two halves. The sentence is for a person: it is read in a
    log, it gets rewritten, and nothing may depend on its wording. The code is
    what a caller branches on: "not enough funds" is a screen, "the basket
    changed" is a re-price. So the sentence is free to change and the code is
    not, and that holds only while every no a module says carries one.

    A builtin exception carries no code at all. A `ValueError` crossing a use
    case is a refusal about which the outside knows only that it happened, and
    the perimeter honestly turns it into a 500: it has nothing else to work
    with. `allow` names the builtins that are not refusals:
    `NotImplementedError` is not a no but a method that does not exist yet,
    and the one exception a reader never mistakes for an answer.

    An error of your own owes a code when it is about the player. One that
    says "the code is written wrong" or "a port broke its promise" is
    internal: nobody branches on it, and `internal` lists its name.

    Settings: `zones`, `carries`, `allow`, `internal`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = RefusalsSettings
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
            model=RefusalsSettings,
            code=CODE,
        )
        where = zoned(
            file=file,
            zones=limits.zones,
        )
        if where is None:
            return
        # By line, not by traversal: `ast.walk` goes breadth-first, and a
        # refusal deep inside an `if` would come out after a neighbour written
        # below it.
        yield from sorted(
            cls._found(
                file=file,
                limits=limits,
            ),
            key=lambda violation: (violation.line, violation.column),
        )

    @classmethod
    def _found(
        cls,
        *,
        file: ParsedFile,
        limits: RefusalsSettings,
    ) -> Iterator[Violation]:
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.Raise) or node.exc is None:
                continue
            raised = cls._raised(thrown=node.exc)
            if not raised:
                continue
            found = cls._said(
                raised=raised,
                thrown=node.exc,
                limits=limits,
            )
            if found is None:
                continue
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                message=found,
            )

    @staticmethod
    def _raised(*, thrown: ast.expr) -> str:
        """What is raised: `raise Denied(...)` and `raise Denied` are the same name."""
        return name(node=thrown.func) if isinstance(thrown, ast.Call) else name(node=thrown)

    @classmethod
    def _said(
        cls,
        *,
        raised: str,
        thrown: ast.expr,
        limits: RefusalsSettings,
    ) -> str | None:
        """What is wrong with this `raise`; `None` means nothing."""
        if raised in BUILTINS:
            if raised in limits.allow:
                return None
            said = f" with {limits.carries}=" if limits.carries else ""
            return (
                f"raises {raised}, which carries no code: all the outside knows about "
                f"this refusal is that it happened. Answer with an error of your own{said}"
            )
        if limits.carries is None or raised in limits.internal:
            return None
        if not isinstance(thrown, ast.Call):
            return f"raises {raised} as a bare class, without {limits.carries}="
        if any(keyword.arg == limits.carries for keyword in thrown.keywords):
            return None
        return (
            f"raises {raised} without {limits.carries}=; the code is what the caller "
            f"branches on, the sentence is for a person"
        )
