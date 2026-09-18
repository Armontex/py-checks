"""Разобранный файл, который получают проверки."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

import libcst

from python_checks.core._errors import ParseError

if TYPE_CHECKING:
    from pathlib import Path


class ParsedFile:
    """Файл, прочитанный один раз и разобранный не больше одного раза.

    Дерево строится лениво и запоминается: проверок на файл много, а разбор
    один. Файлам, которым дерево не нужно (длина модуля, например), платить за
    него не приходится.

    Деревьев два, и оба ленивые. `tree` — обычный `ast`: быстрый, его хватает,
    когда правило только смотрит. `module` — дерево `libcst`, в котором есть
    комментарии, кавычки и пробелы: такое дерево можно переписать и отдать
    обратно текстом, ничего чужого не потеряв. Правило берёт то, что ему нужно,
    и за второй разбор платит только оно.
    """

    __slots__ = ("_lines", "_module", "_text", "_tree", "path", "source")

    def __init__(self, *, path: Path, text: str, source: Path | None = None) -> None:
        self.path = path
        # Корень исходников проекта: по нему правила, которые говорят о месте
        # («ORM живёт в `infra/database`»), считают адрес файла. Угадывать его
        # по `__init__.py` нельзя — папка без него встречается и внутри пакета.
        self.source = source
        self._text = text
        self._tree: ast.Module | None = None
        self._module: libcst.Module | None = None
        self._lines: tuple[str, ...] | None = None

    @classmethod
    def from_path(cls, *, path: Path, source: Path | None = None) -> ParsedFile:
        return cls(path=path, text=path.read_text(encoding="utf-8"), source=source)

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
