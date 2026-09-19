"""Функции модуля и то, что о них знает только дерево."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterator

# Единственный способ для метода не получить первый аргумент от интерпретатора.
STATIC: Final = "staticmethod"

type Function = ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True, slots=True)
class Definition:
    """Функция, её имя вида `Класс.метод` и то, метод ли она.

    Первый аргумент метода передаёт интерпретатор, и автор подписи тут ни при
    чём — но узнаётся это по месту, а не по имени. `self` в обычной функции или
    в `@staticmethod` — обычный аргумент.
    """

    name: str
    node: Function
    method: bool


def definitions(
    *,
    node: ast.AST,
    prefix: str = "",
    method: bool = False,
) -> Iterator[Definition]:
    """Все функции дерева под именами вида `Класс.метод` или `внешняя.вложенная`.

    Заодно запоминается, тело какого узла мы разбираем: функция в теле класса —
    метод, а функция внутри метода — уже нет, и первый аргумент ей никто не
    передаёт.
    """
    for child in ast.iter_child_nodes(node):
        match child:
            case ast.ClassDef(name=name):
                yield from definitions(
                    node=child,
                    prefix=f"{prefix}{name}.",
                    method=True,
                )
            case ast.FunctionDef(name=name) | ast.AsyncFunctionDef(name=name):
                yield Definition(
                    name=f"{prefix}{name}",
                    node=child,
                    method=method,
                )
                yield from definitions(
                    node=child,
                    prefix=f"{prefix}{name}.",
                    method=False,
                )
            case _:
                yield from definitions(
                    node=child,
                    prefix=prefix,
                    method=method,
                )


def receiver(*, definition: Definition) -> int:
    """Сколько первых аргументов передаёт интерпретатор: один у метода, иначе ноль."""
    if not definition.method or static(node=definition.node):
        return 0
    return 1


def static(*, node: Function) -> bool:
    return STATIC in {name(node=item) for item in node.decorator_list}


def name(*, node: ast.expr) -> str:
    match node:
        case ast.Name(id=found) | ast.Attribute(attr=found):
            return found
        case _:
            return ""


def signature_end(*, node: Function) -> int:
    """Последняя строка подписи: на ней стоит пометка, если подпись в столбик."""
    return max(node.body[0].lineno - 1, node.lineno)
