"""Нарушение и то, как оно выглядит в выводе."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import ast
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class Violation:
    """Одно нарушение: где, чем и почему.

    Строка и колонка нумеруются с единицы, как их показывает редактор. У `ast`
    колонка начинается с нуля, поэтому узлы дерева превращаются в нарушение
    через `from_node`, а не вручную.
    """

    path: Path
    line: int
    column: int
    code: str
    message: str

    @classmethod
    def from_node(
        cls,
        *,
        node: ast.AST,
        path: Path,
        code: str,
        message: str,
    ) -> Violation:
        line = getattr(node, "lineno", 1)
        column = getattr(node, "col_offset", 0)
        return cls(path=path, line=line, column=column + 1, code=code, message=message)

    def render(self, *, root: Path | None = None) -> str:
        """`путь:строка:колонка: код: сообщение`.

        Формат выбран не ради красоты: по нему строку понимают редактор, `grep`
        и CI, и по ней можно перейти к месту одним щелчком.
        """
        path = self.path
        if root is not None:
            with suppress(ValueError):
                path = path.relative_to(root)
        return f"{path}:{self.line}:{self.column}: {self.code}: {self.message}"
