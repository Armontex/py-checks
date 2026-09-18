"""Где файл лежит внутри своего пакета.

Правило про импорты говорит о месте: «sqlalchemy живёт в `infra/database`».
Место считается от корня исходников, который известен ядру из настроек.
Угадывать его по `__init__.py` нельзя: папка без него встречается и посреди
пакета — в одном из сервисов так лежит половина репозиториев.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, NamedTuple

if TYPE_CHECKING:
    from pathlib import Path

    from python_checks.core import ParsedFile

INIT: Final = "__init__"

# Пакет и хотя бы один шаг внутри него: файл, лежащий прямо в корне исходников,
# ни в каком пакете не находится, и говорить о его месте нечего.
INSIDE: Final = 2


class Place(NamedTuple):
    """Корневой пакет файла и его адрес внутри этого пакета."""

    package: str
    parts: tuple[str, ...]

    @property
    def where(self) -> str:
        return "/".join(self.parts)

    def under(self, *, prefix: str) -> bool:
        """Лежит ли файл под этим путём; пустой путь не разрешает ничего."""
        if not prefix:
            return False
        wanted = tuple(prefix.split("/"))
        return self.parts[: len(wanted)] == wanted


def place(*, file: ParsedFile) -> Place | None:
    """Адрес файла; `None`, если корень исходников неизвестен или файл вне его."""
    if file.source is None:
        return None
    relative = _relative(path=file.path, source=file.source)
    if relative is None or len(relative) < INSIDE:
        return None
    parts = relative[1:]
    if parts[-1] == INIT:
        parts = parts[:-1]
    return Place(package=relative[0], parts=parts)


def _relative(*, path: Path, source: Path) -> tuple[str, ...] | None:
    try:
        inside = path.resolve().relative_to(source.resolve())
    except ValueError:
        return None
    return inside.with_suffix("").parts
