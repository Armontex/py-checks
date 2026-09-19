"""Имена: как их читают в дереве и как сверяют с записанным в настройках.

Правила говорят именами: «база называется `Base`», «эта колонка объявлена
`mapped_column`», «`datetime.now` берут портом». Спросить у узла, как его
зовут, — не дело каждого правила: способ один на язык, и живёт он здесь.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

DOT: Final = "."
ANY: Final = "*"


def name(*, node: ast.expr) -> str:
    """Как это зовут; пустая строка, если именем это не назвать.

    Строковая аннотация (`-> "Order"`) — это имя, написанное буквами:
    отличать её от обычной незачем, автор имел в виду то же самое. А вот вызов
    и подписанное выражение именем не считаются: `tuple(...)[:1]` — это срез
    списка, и правило про формы типов не должно принять его за объявление.
    Развернуть их просит тот, кто читает базы и декораторы, — `names`.
    """
    match node:
        case ast.Name(id=found) | ast.Attribute(attr=found) | ast.Constant(value=str() as found):
            return found
        case _:
            return ""


def names(*, nodes: Iterable[ast.expr]) -> Iterator[str]:
    """Имена перечисленного: баз класса, декораторов.

    Здесь имя и правда стоит за вызовом и за подстановкой: `@dataclass(frozen=True)`
    — это `dataclass`, `Generic[T]` — это `Generic`.
    """
    for node in nodes:
        if found := name(node=_head(node=node)):
            yield found


def _head(*, node: ast.expr) -> ast.expr:
    """Из чего сделано выражение: с кого начали, прежде чем звать и подставлять."""
    match node:
        case ast.Call(func=inner) | ast.Subscript(value=inner):
            return _head(node=inner)
        case _:
            return node


def walked(*, node: ast.expr) -> Iterator[str]:
    """Все имена внутри выражения, на любой глубине и в порядке написания.

    `dict[str, Order | None]` — это `dict`, `str`, `Order`: правило про
    аннотации смотрит на то, что в ней названо, а не на её форму. Имя, взятое
    в кавычки, — такое же имя: ссылка вперёд написана строкой не по смыслу, а
    потому что в этом месте класса ещё нет.
    """
    for child in ast.walk(node):
        if isinstance(child, ast.Name | ast.Attribute | ast.Constant) and (
            found := name(node=child)
        ):
            yield found


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
