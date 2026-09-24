"""The parsed file the checks receive."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

import libcst

from py_checks.core._errors import ParseError

if TYPE_CHECKING:
    from pathlib import Path


class ParsedFile:
    """A file read once and parsed no more than once.

    The tree is built lazily and remembered: there are many checks per file,
    and one parse. Checks that need no tree (module length, for one) do not
    pay for it.

    There are two trees, both lazy. `tree` is the plain `ast`: fast, and enough
    when a rule only looks. `module` is the `libcst` tree, which keeps comments,
    quotes and whitespace: such a tree can be rewritten and handed back as
    text without losing anything that is not ours. A rule takes what it needs,
    and only that rule pays for the second parse.
    """

    __slots__ = ("_lines", "_module", "_text", "_tree", "path", "source")

    def __init__(
        self,
        *,
        path: Path,
        text: str,
        source: Path | None = None,
    ) -> None:
        self.path = path
        # The root of the project's sources: rules that speak about place ("the
        # ORM lives in `infra/database`") work out a file's address from it. It
        # cannot be guessed from `__init__.py` — a folder without one turns up
        # inside a package too.
        self.source = source
        self._text = text
        self._tree: ast.Module | None = None
        self._module: libcst.Module | None = None
        self._lines: tuple[str, ...] | None = None

    @classmethod
    def from_path(
        cls,
        *,
        path: Path,
        source: Path | None = None,
    ) -> ParsedFile:
        return cls(
            path=path,
            text=path.read_text(encoding="utf-8"),
            source=source,
        )

    @property
    def text(self) -> str:
        return self._text

    @property
    def lines(self) -> tuple[str, ...]:
        if self._lines is None:
            self._lines = tuple(self._text.splitlines())
        return self._lines

    @property
    def tree(self) -> ast.Module:
        if self._tree is None:
            try:
                self._tree = ast.parse(self._text, filename=str(self.path))
            except SyntaxError as error:
                raise ParseError(
                    path=self.path,
                    error=error,
                ) from error
        return self._tree

    @property
    def module(self) -> libcst.Module:
        if self._module is None:
            try:
                self._module = libcst.parse_module(self._text)
            except libcst.ParserSyntaxError as error:
                raise ParseError(
                    path=self.path,
                    error=SyntaxError(error.message),
                ) from error
        return self._module
