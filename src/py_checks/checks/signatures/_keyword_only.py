"""Every argument is passed by name."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks.signatures._functions import (
    Definition,
    definitions,
    receiver,
    signature_end,
)
from py_checks.checks.signatures._marker import MARKER
from py_checks.config import CheckSettings
from py_checks.core import Edit, Scope, Violation, column

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.checks.signatures._functions import Function
    from py_checks.core import ParsedFile

CODE: Final = "keyword-only-arguments"

# The dunders our own code calls: calling them is a call like any other. The
# other dunders are called by the interpreter, and their signature is not ours.
OWN_DUNDERS: Final[frozenset[str]] = frozenset({"__init__", "__new__", "__call__"})


class KeywordOnlyArguments:
    """Fails when a signature is not written out in full.

    Every argument is passed by name, so a call site reads as documentation,
    and arguments can be reordered without breaking calls:

        def price(*, market: Market, stake: Money) -> Money: ...

    `*args` and `**kwargs` are banned for the same reason: a collector accepts
    anything, there are no types to check, and the call site explains nothing.
    `--fix` leaves them alone: the author picks the argument names that replace
    the stars.

    A callback or a wrapper whose signature a library dictates is marked in
    the signature: `def f(a): ...  # check-ok: keyword-only-arguments: sqlalchemy`.
    The group word `# signature-ok` is understood as well.

    Settings: none.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = CheckSettings
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = MARKER

    def run(
        self,
        *,
        file: ParsedFile,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        _ = settings
        for definition in definitions(node=file.tree):
            if self._interpreter_dunder(name=definition.name):
                continue
            yield from self._violations(
                definition=definition,
                file=file,
            )

    @classmethod
    def _violations(
        cls,
        *,
        definition: Definition,
        file: ParsedFile,
    ) -> Iterator[Violation]:
        node, name = definition.node, definition.name
        end_line = signature_end(node=node)
        if positional := cls._positional(definition=definition):
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                message=(
                    f"{name} takes {', '.join(positional)} by position; put a `*` before them"
                ),
                end_line=end_line,
                edit=cls._star(
                    definition=definition,
                    file=file,
                ),
            )
        if collected := cls._collectors(node=node):
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                message=f"{name} takes {', '.join(collected)}; list the arguments by name",
                end_line=end_line,
            )

    @staticmethod
    def _interpreter_dunder(*, name: str) -> bool:
        own = name.rsplit(".", maxsplit=1)[-1]
        if own in OWN_DUNDERS:
            return False
        return own.startswith("__") and own.endswith("__")

    @staticmethod
    def _positional(*, definition: Definition) -> tuple[str, ...]:
        """The arguments a caller can pass by position."""
        skip = receiver(definition=definition)
        arguments = [*definition.node.args.posonlyargs, *definition.node.args.args]
        return tuple(argument.arg for argument in arguments[skip:])

    @staticmethod
    def _collectors(*, node: Function) -> tuple[str, ...]:
        """`*args` and `**kwargs` as the caller sees them."""
        stars = ((node.args.vararg, "*"), (node.args.kwarg, "**"))
        return tuple(f"{star}{argument.arg}" for argument, star in stars if argument)

    @staticmethod
    def _star(
        *,
        definition: Definition,
        file: ParsedFile,
    ) -> Edit | None:
        """The edit: a `*` before the first argument that is now positional.

        Not for every case. With `*args` a second star does not fit in the
        signature, and with `/` the arguments are positional because the
        author asked for it, and overruling the author is not an autofix's
        place.
        """
        node = definition.node
        if node.args.vararg is not None or node.args.posonlyargs:
            return None
        first = node.args.args[receiver(definition=definition)]
        line = first.lineno
        at = column(
            line=file.lines[line - 1],
            offset=first.col_offset,
        )
        return Edit(
            line=line,
            column=at,
            end_line=line,
            end_column=at,
            text="*, ",
        )
