"""A violation and how it looks in the output."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import ast
    from pathlib import Path

    from py_checks.core._edit import Edit


@dataclass(frozen=True, slots=True)
class Violation:
    """One violation: where, by what rule and why.

    Line and column count from 1, as the editor shows them. In `ast` the
    column starts at 0, so tree nodes become a violation through `from_node`,
    not by hand.

    `end_line` is needed only by violations that span several lines: the core
    uses it to look for a mark across the whole signature, not just its first
    line.

    `edit` is present on a violation the rule knows how to fix. The violation
    carries the edit itself, not a separate pass: whoever found the place knows
    the most about it, and there is no reason to parse the file a second time
    to fix it.
    """

    path: Path
    line: int
    column: int
    code: str
    message: str
    end_line: int | None = None
    edit: Edit | None = None

    @classmethod
    def from_node(
        cls,
        *,
        node: ast.AST,
        path: Path,
        code: str,
        message: str,
        end_line: int | None = None,
        edit: Edit | None = None,
    ) -> Violation:
        line = getattr(node, "lineno", 1)
        column = getattr(node, "col_offset", 0)
        return cls(
            path=path,
            line=line,
            column=column + 1,
            code=code,
            message=message,
            end_line=end_line,
            edit=edit,
        )

    def render(self, *, root: Path | None = None) -> str:
        """`path:line:column: code: message`.

        The format is not chosen for looks: the editor, `grep` and CI all
        understand a line by it, and it takes one click to jump to the place.
        """
        path = self.path
        if root is not None:
            with suppress(ValueError):
                path = path.relative_to(root)
        return f"{path}:{self.line}:{self.column}: {self.code}: {self.message}"
