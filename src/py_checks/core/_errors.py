"""Errors of the core."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class ParseError(Exception):
    """The file does not parse: the syntax is broken."""

    def __init__(
        self,
        *,
        path: Path,
        error: SyntaxError,
    ) -> None:
        super().__init__(f"{path}: {error.msg}")
        self.path = path
        self.error = error


class UnknownCheckError(Exception):
    """There is no such check."""

    def __init__(
        self,
        *,
        code: str,
        known: tuple[str, ...],
    ) -> None:
        super().__init__(f"unknown check {code!r}; available: {', '.join(known)}")
        self.code = code
