"""The nesting depth of control structures."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final, Self

from pydantic import model_validator

from py_checks.checks.signatures._marker import MARKER
from py_checks.config import OPEN, CheckSettings
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.core import ParsedFile

CODE: Final = "nesting"

# The kinds the rule can speak about. `with` is on the list, but a project has
# no reason to keep it in its table: a nested `with` is caught by ruff `SIM117`,
# with an autofix and a ready answer, "make it one `with a, b:`".
KINDS: Final[dict[str, tuple[type[ast.stmt], ...]]] = {
    "try": (ast.Try, ast.TryStar),
    "with": (ast.With, ast.AsyncWith),
    "if": (ast.If,),
    "for": (ast.For, ast.AsyncFor),
    "while": (ast.While,),
    "match": (ast.Match,),
}

# The statement lists a node holds inside it.
BRANCHES: Final[tuple[str, ...]] = ("body", "orelse", "finalbody")


class NestingSettings(CheckSettings):
    """The `[nesting]` section: a construct and its nesting limit."""

    model_config = OPEN

    __pydantic_extra__: dict[str, int]  # type: ignore[assignment]

    @property
    def limits(self) -> dict[str, int]:
        return self.__pydantic_extra__

    @model_validator(mode="after")
    def _known(self) -> Self:
        unknown = sorted(set(self.limits) - set(KINDS))
        if unknown:
            message = f"unknown constructs: {', '.join(unknown)}"
            raise ValueError(message)
        if any(limit < 1 for limit in self.limits.values()):
            message = "a nesting limit is an integer of at least one"
            raise ValueError(message)
        return self


class Nesting:
    """Fails when control structures are nested deeper than the limit.

    Depth is where logic stops being read and starts being decoded. Each kind
    has its own limit because they cost different things: a second `try`
    inside the first hides which line threw, while a second level of `if` is
    an ordinary fork, and the third is the one too many.

    An `elif` is a branch, not a level, and is not counted as one. An `else:`
    written out with an `if` inside is counted: that is the extra indent.

    A nested `with` is better left out of the table: ruff `SIM117` catches it,
    with an autofix and the answer on the spot.

    Settings: the construct's name and its limit, `try = 1`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = NestingSettings
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
            model=NestingSettings,
            code=CODE,
        ).limits
        if not limits:
            return
        depths = dict.fromkeys(limits, 0)
        for node in file.tree.body:
            yield from cls._visit(
                file=file,
                node=node,
                depths=depths,
                limits=limits,
            )

    @classmethod
    def _visit(
        cls,
        *,
        file: ParsedFile,
        node: ast.stmt,
        depths: dict[str, int],
        limits: dict[str, int],
    ) -> Iterator[Violation]:
        kind = cls._kind(
            node=node,
            limits=limits,
        )
        if kind is not None:
            depth = depths[kind] + 1
            if depth > limits[kind]:
                yield Violation.from_node(
                    node=node,
                    path=file.path,
                    code=CODE,
                    message=f"{kind} nested {depth} deep, the limit is {limits[kind]}",
                )
            depths = {**depths, kind: depth}
        for child in cls._children(node=node):
            inner = depths
            if isinstance(node, ast.If) and cls._elif(
                node=node,
                child=child,
            ):
                inner = {**depths, "if": depths["if"] - 1}
            yield from cls._visit(
                file=file,
                node=child,
                depths=inner,
                limits=limits,
            )

    @staticmethod
    def _kind(
        *,
        node: ast.stmt,
        limits: dict[str, int],
    ) -> str | None:
        return next((kind for kind in limits if isinstance(node, KINDS[kind])), None)

    @staticmethod
    def _children(*, node: ast.stmt) -> Iterator[ast.stmt]:
        for field in BRANCHES:
            yield from getattr(node, field, [])
        for handler in getattr(node, "handlers", []):
            yield from handler.body

    @staticmethod
    def _elif(
        *,
        node: ast.If,
        child: ast.stmt,
    ) -> bool:
        """An `elif` stands in the same column as its `if`; a written-out `else: if` does not."""
        return isinstance(child, ast.If) and child.col_offset == node.col_offset
