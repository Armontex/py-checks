"""Ошибки ядра."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class ParseError(Exception):
    """Файл не разбирается: синтаксис сломан."""

    def __init__(self, *, path: Path, error: SyntaxError) -> None:
        super().__init__(f"{path}: {error.msg}")
        self.path = path
        self.error = error


class UnknownCheckError(Exception):
    """Такой проверки нет."""

    def __init__(self, *, code: str, known: tuple[str, ...]) -> None:
        super().__init__(f"неизвестная проверка {code!r}; есть: {', '.join(known)}")
        self.code = code
