"""A list of two or more entries is written in a column."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks.signatures._functions import definitions, receiver
from py_checks.checks.signatures._marker import MARKER
from py_checks.config import CheckSettings
from py_checks.core import Edit, Scope, Violation, column, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from py_checks.checks.signatures._functions import Definition, Function
    from py_checks.core import ParsedFile

CODE: Final = "signature-layout"

# Two entries are enough: one on a line reads as a single word, while two
# already have to be taken apart.
ENOUGH: Final = 2


class SignatureLayoutSettings(CheckSettings):
    calls: bool = True


class SignatureLayout:
    """Fails when a list of two or more entries is written on one line.

    Both halves of a call: the signature that declares the parameters, and the
    site that passes them. In a column, editing one argument touches one line
    and says exactly that; the same list on one line shifts everything after
    the edit, and review reads the whole of it to find the change. At a call
    site this matters more than in a signature: expressions stand there, not
    names.

    `self` and `cls` do not count: the interpreter passes them.

    At a call site the rule fires on two or more NAMED arguments, and that is
    the entire border between our code and other people's: every function of
    ours is keyword-only, so a call of ours is all names and falls under the
    rule, while `isinstance(node, ast.Call)` and `range(1, 10)` are somebody
    else's positional signature and are left alone. Once it fires, every
    argument goes into the column, positional ones included: a call unfolded
    halfway is of no use to the rule.

    A decorator is the single exception: `@dataclass(frozen=True, slots=True)`
    is a label, not a list read for meaning. The same words sit on every
    dataclass in a service, and there is nothing to rearrange.

    `--fix` writes the trailing comma and calls `ruff format`: the formatter
    keeps a list in a column when the comma is there, but never writes one.

    Settings: `calls`, whether call sites are judged. The half about calls
    costs more than the half about signatures: in a service written without
    it, it touches nearly every file, and switching it off for the duration of
    a move is more honest than switching off the whole rule.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = SignatureLayoutSettings
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(
        cls,
        *,
        file: ParsedFile,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        calls = settings_as(
            settings=settings,
            model=SignatureLayoutSettings,
            code=CODE,
        ).calls
        for definition in definitions(node=file.tree):
            yield from cls._signature(
                file=file,
                definition=definition,
            )
        if not calls:
            return
        marks = cls._decorators(tree=file.tree)
        for node in ast.walk(file.tree):
            if isinstance(node, ast.Call) and id(node) not in marks:
                yield from cls._call(
                    file=file,
                    node=node,
                )

    @classmethod
    def _signature(
        cls,
        *,
        file: ParsedFile,
        definition: Definition,
    ) -> Iterator[Violation]:
        node = definition.node
        listed = cls._parameters(definition=definition)
        defaults = cls._defaults(node=node)
        if len(listed) < ENOUGH or cls._columned(
            listed=listed,
            after=node.lineno,
        ):
            return
        yield Violation.from_node(
            node=node,
            path=file.path,
            code=CODE,
            message=(f"{definition.name}: {len(listed)} parameters on one line; put one per line"),
            edit=cls._comma(
                file=file,
                ends=[*cls._ends(nodes=listed), *cls._ends(nodes=defaults)],
            ),
        )

    @classmethod
    def _call(
        cls,
        *,
        file: ParsedFile,
        node: ast.Call,
    ) -> Iterator[Violation]:
        listed: list[ast.expr | ast.keyword] = [*node.args, *node.keywords]
        if len(node.keywords) < ENOUGH:
            return
        after = node.func.end_lineno or node.func.lineno
        if cls._columned(
            listed=listed,
            after=after,
        ):
            return
        yield Violation.from_node(
            node=node,
            path=file.path,
            code=CODE,
            message=(
                f"{cls._called(node=node)}: {len(listed)} arguments on one line; put one per line"
            ),
            edit=cls._comma(
                file=file,
                ends=cls._ends(nodes=listed),
            ),
        )

    @staticmethod
    def _columned(
        *,
        listed: Sequence[ast.expr | ast.keyword | ast.arg],
        after: int,
    ) -> bool:
        """One per line, and none on the line where the list opened."""
        lines = {element.lineno for element in listed}
        return len(lines) == len(listed) and min(lines) > after

    @staticmethod
    def _parameters(*, definition: Definition) -> list[ast.arg]:
        """The parameters a caller fills, in the order written."""
        arguments = definition.node.args
        listed = [
            *arguments.posonlyargs,
            *arguments.args,
            *([arguments.vararg] if arguments.vararg else []),
            *arguments.kwonlyargs,
            *([arguments.kwarg] if arguments.kwarg else []),
        ]
        return listed[receiver(definition=definition) :]

    @staticmethod
    def _defaults(*, node: Function) -> list[ast.expr]:
        """Default values: the comma goes after them, not after the name."""
        return [one for one in (*node.args.defaults, *node.args.kw_defaults) if one is not None]

    @staticmethod
    def _ends(*, nodes: Sequence[ast.expr | ast.keyword | ast.arg]) -> list[tuple[int, int]]:
        """Where each entry of the list ends."""
        return [
            (node.end_lineno, node.end_col_offset)
            for node in nodes
            if node.end_lineno is not None and node.end_col_offset is not None
        ]

    @staticmethod
    def _comma(
        *,
        file: ParsedFile,
        ends: list[tuple[int, int]],
    ) -> Edit | None:
        """The edit: a trailing comma after the last entry of the list.

        Last by where it ends, not by the order written: for a parameter with a
        default value the comma goes after the value, not after the name.

        The layout from there on is the formatter's job: `ruff format` unfolds
        the list into a column as soon as the comma is there.
        """
        if not ends:
            return None
        line, offset = max(ends)
        at = column(
            line=file.lines[line - 1],
            offset=offset,
        )
        return Edit(
            line=line,
            column=at,
            end_line=line,
            end_column=at,
            text=",",
        )

    @staticmethod
    def _called(*, node: ast.Call) -> str:
        """How the call is written: `self._policy`, `price`, `Model.build`."""
        return ast.unparse(node.func)

    @staticmethod
    def _decorators(*, tree: ast.Module) -> frozenset[int]:
        """The calls that are in fact decorators, by node identity."""
        return frozenset(
            id(decorator)
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
            for decorator in node.decorator_list
            if isinstance(decorator, ast.Call)
        )
