"""Имя вызываемого и то, как оно сверяется с записанным в настройках."""

from __future__ import annotations

from typing import Final

DOT: Final = "."
ANY: Final = "*"


def matches(
    *,
    called: str,
    pattern: str,
) -> bool:
    """Хвост имени: `datetime.now` — это и `datetime.datetime.now`.

    `random.*` подходит любому вызову модуля целиком: важен не последний
    кусок, а то, у кого его взяли.
    """
    parts = called.split(DOT)
    wanted = pattern.split(DOT)
    if wanted[-1] == ANY:
        head = wanted[:-1]
        return len(parts) > len(head) and parts[-len(head) - 1 : -1] == head
    return len(parts) >= len(wanted) and parts[-len(wanted) :] == wanted
