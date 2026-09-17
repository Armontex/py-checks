"""Разобранный файл, который получают проверки."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from python_checks.core._errors import ParseError

if TYPE_CHECKING:
    from pathlib import Path


class ParsedFile:
    """Файл, прочитанный один раз и разобранный не больше одного раза.

    Дерево строится лениво и запоминается: проверок на файл много, а разбор
    один. Файлам, которым дерево не нужно (длина модуля, например), платить за
    него не приходится.
    """

    __slots__ = ("_lines", "_text", "_tree", "path")

    def __init__(self, *, path: Path, text: str) -> None:
        self.path = path
        self._text = text
        self._tree: ast.Module | None = None
        self._lines: tuple[str, ...] | None = None

    @classmethod
    def from_path(cls, *, path: Path) -> ParsedFile:
        return cls(path=path, text=path.read_text(encoding="utf-8"))

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
                raise ParseError(path=self.path, error=error) from error
        return self._tree
