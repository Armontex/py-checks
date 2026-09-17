"""Нарушение и то, как оно выглядит в выводе."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import ast
    from pathlib import Path

    from python_checks.core._edit import Edit


@dataclass(frozen=True, slots=True)
class Violation:
    """Одно нарушение: где, чем и почему.

    Строка и колонка нумеруются с единицы, как их показывает редактор. У `ast`
    колонка начинается с нуля, поэтому узлы дерева превращаются в нарушение
    через `from_node`, а не вручную.

    `end_line` нужен только тем нарушениям, которые занимают несколько строк:
    по нему ядро ищет маркер во всей подписи, а не в одной её первой строке.

    `edit` есть у нарушения, которое правило умеет исправить. Правку несёт само
    нарушение, а не отдельный проход: тот, кто нашёл место, знает о нём больше
    всех, и второй раз разбирать файл ради починки незачем.
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
        """`путь:строка:колонка: код: сообщение`.

        Формат выбран не ради красоты: по нему строку понимают редактор, `grep`
        и CI, и по ней можно перейти к месту одним щелчком.
        """
        path = self.path
        if root is not None:
            with suppress(ValueError):
                path = path.relative_to(root)
        return f"{path}:{self.line}:{self.column}: {self.code}: {self.message}"
