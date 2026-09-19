"""Где файл лежит внутри своего пакета.

Правило про импорты говорит о месте: «sqlalchemy живёт в `infra/database`».
Место считается от корня исходников, который известен ядру из настроек.
Угадывать его по `__init__.py` нельзя: папка без него встречается и посреди
пакета — в одном из сервисов так лежит половина репозиториев.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pathlib import Path

    from python_checks.core import ParsedFile

INIT: Final = "__init__"

SEPARATOR: Final = "/"

# Один любой кусок пути: `modules/*/domain` — домен любого модуля.
ANY: Final = "*"

# Пакет и хотя бы один шаг внутри него: файл, лежащий прямо в корне исходников,
# ни в каком пакете не находится, и говорить о его месте нечего.
INSIDE: Final = 2


@dataclass(frozen=True, slots=True)
class Place:
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
        wanted = tuple(prefix.split(SEPARATOR))
        return self.parts[: len(wanted)] == wanted

    def holds(self, *, path: str) -> bool:
        """Идут ли эти куски адреса подряд где угодно внутри него.

        Адрес включает имя модуля, поэтому `exceptions` подходит и как
        директория, и как файл `exceptions.py`: для словаря отказов это одно и
        то же место.
        """
        return (
            _run(
                parts=self.parts,
                wanted=path,
            )
            is not None
        )

    def within(self, *, directory: str) -> int | None:
        """Где кончается самое глубокое вхождение этих директорий, или `None`.

        Имя файла в счёт не идёт: речь о директории, а не о модуле. Конец, а не
        начало, потому что сравнивать вложенность двух ключей разной длины
        можно только по тому, где они кончаются, — глубже тот, кто кончается
        позже.
        """
        return _run(
            parts=self.parts[:-1],
            wanted=directory,
        )


def place(*, file: ParsedFile) -> Place | None:
    """Адрес файла; `None`, если корень исходников неизвестен или файл вне его."""
    if file.source is None:
        return None
    relative = _relative(
        path=file.path,
        source=file.source,
    )
    if relative is None or len(relative) < INSIDE:
        return None
    parts = relative[1:]
    if parts[-1] == INIT:
        parts = parts[:-1]
    return Place(
        package=relative[0],
        parts=parts,
    )


def _relative(
    *,
    path: Path,
    source: Path,
) -> tuple[str, ...] | None:
    try:
        inside = path.resolve().relative_to(source.resolve())
    except ValueError:
        return None
    return inside.with_suffix("").parts


def _run(
    *,
    parts: tuple[str, ...],
    wanted: str,
) -> int | None:
    """Конец последнего вхождения подряд идущих кусков пути.

    `*` подходит любому одному куску: `modules/*/domain` — это домен любого
    модуля, и перечислять модули по именам не нужно.
    """
    needle = tuple(wanted.split(SEPARATOR))
    span = len(needle)
    ends = [
        start + span
        for start in range(len(parts) - span + 1)
        if _same(
            found=parts[start : start + span],
            needle=needle,
        )
    ]
    return max(ends) if ends else None


def _same(
    *,
    found: tuple[str, ...],
    needle: tuple[str, ...],
) -> bool:
    return all(wanted in (ANY, part) for part, wanted in zip(found, needle, strict=True))
