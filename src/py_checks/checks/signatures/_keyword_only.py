"""Every argument is passed by name."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks.signatures._callers import callers
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
    import ast
    from collections.abc import Iterator, Sequence
    from pathlib import Path

    from py_checks.checks.signatures._functions import Function
    from py_checks.core import ParsedFile, Repair

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

    def repair(
        self,
        *,
        violations: Sequence[Violation],
        root: Path,
        source: Path,
    ) -> Repair:
        """`--fix` names the arguments at every call, or changes nothing."""
        return callers(
            violations=violations,
            root=root,
            source=source,
            star=self._star,
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
        signature. Arguments before `/` are positional because the author
        asked for it, and overruling the author is not an autofix's place: the
        star goes after `/`.
        """
        arguments = definition.node.args
        if arguments.vararg is not None:
            return None
        skip = max(receiver(definition=definition) - len(arguments.posonlyargs), 0)
        if len(arguments.args) <= skip:
            return None
        start = _position(
            file=file,
            node=arguments.args[skip],
        )
        if arguments.kwonlyargs:
            return _moved(
                file=file,
                arguments=arguments,
                start=start,
            )
        return Edit(
            line=start[0],
            column=start[1],
            end_line=start[0],
            end_column=start[1],
            text="*, ",
        )


def _moved(
    *,
    file: ParsedFile,
    arguments: ast.arguments,
    start: tuple[int, int],
) -> Edit:
    """The bare `*` the signature already has, moved to the front: two do not compile."""
    last = _position(
        file=file,
        node=(arguments.defaults or arguments.args)[-1],
        end=True,
    )
    end = _position(
        file=file,
        node=arguments.kwonlyargs[0],
    )
    between = _between(
        file=file,
        start=last,
        end=end,
    )
    star = between.index("*")
    return Edit(
        line=start[0],
        column=start[1],
        end_line=end[0],
        end_column=end[1],
        # The star travels with what follows it, so a signature written one
        # argument per line keeps that shape.
        text=(
            between[star:]
            + _between(
                file=file,
                start=start,
                end=last,
            )
            + between[:star]
        ),
    )


def _position(
    *,
    file: ParsedFile,
    node: ast.expr | ast.arg,
    end: bool = False,
) -> tuple[int, int]:
    """Where the node starts or ends, as an edit counts it: line and column from 1."""
    line = node.end_lineno if end else node.lineno
    offset = node.end_col_offset if end else node.col_offset
    if line is None or offset is None:
        message = "a parsed node always has a position"
        raise AssertionError(message)
    return line, column(
        line=file.lines[line - 1],
        offset=offset,
    )


def _between(
    *,
    file: ParsedFile,
    start: tuple[int, int],
    end: tuple[int, int],
) -> str:
    """The source text between two positions, line breaks as written."""
    lines = file.text.splitlines(keepends=True)[start[0] - 1 : end[0]]
    if len(lines) == 1:
        return lines[0][start[1] - 1 : end[1] - 1]
    return lines[0][start[1] - 1 :] + "".join(lines[1:-1]) + lines[-1][: end[1] - 1]
