"""Совпадение адреса с путём.

Адрес в настройках — не префикс и не имя директории, а подряд идущие куски
пути: `application/use_cases` находится и внутри `modules/<имя>/`. Правила
спрашивают этим, лежит ли файл в названном месте; команда `doctor` — тем же
самым, существует ли вообще директория, о которой говорит настройка. Вопрос
один, значит и ответчик один: два похожих сравнения разъехались бы, и `doctor`
успокаивал бы насчёт адреса, мимо которого правило проходит.
"""

from __future__ import annotations

from typing import Final

SEPARATOR: Final = "/"

# Один любой кусок пути: `modules/*/domain` — домен любого модуля.
ANY: Final = "*"


def depth(
    *,
    parts: tuple[str, ...],
    path: str,
) -> int | None:
    """Конец последнего вхождения подряд идущих кусков пути, или `None`.

    Конец, а не начало: сравнивать вложенность двух адресов разной длины можно
    только по тому, где они кончаются, — глубже тот, кто кончается позже.
    """
    needle = tuple(path.split(SEPARATOR))
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
