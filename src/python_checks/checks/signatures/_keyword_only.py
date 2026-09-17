"""Все аргументы передаются по имени."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from python_checks.config import CheckSettings
from python_checks.core import Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from python_checks.core import ParsedFile

CODE: Final = "keyword-only-arguments"

type Definition = ast.FunctionDef | ast.AsyncFunctionDef

# Передаются интерпретатором позиционно, автор подписи тут ни при чём.
IMPLICIT: Final[frozenset[str]] = frozenset({"self", "cls"})

# Дандеры, которые зовёт наш собственный код: их вызов — такой же вызов, как
# любой другой. Остальные дандеры зовёт интерпретатор, и подпись у них не наша.
OWN_DUNDERS: Final[frozenset[str]] = frozenset({"__init__", "__new__", "__call__"})


class KeywordOnlySettings(CheckSettings):
    marker: str = "# signature-ok"


class KeywordOnlyArguments:
    """Падает, если подпись записана не полностью.

    Каждый аргумент передаётся по имени, поэтому место вызова читается как
    документация, а аргументы можно менять местами, не ломая вызовы:

        def price(*, market: Market, stake: Money) -> Money: ...

    `*args` и `**kwargs` запрещены по той же причине: сборщик принимает что
    угодно, проверять типы там нечего, а место вызова ничего не объясняет.

    Обратный вызов или обёртка, чью подпись диктует библиотека, помечается в
    строке подписи: `def f(a): ...  # signature-ok: sqlalchemy`.

    Настройка: `marker`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = KeywordOnlySettings

    def run(self, *, file: ParsedFile, settings: CheckSettings) -> Iterator[Violation]:
        marker = settings_as(settings=settings, model=KeywordOnlySettings, code=CODE).marker
        for name, node in _definitions(node=file.tree):
            if _interpreter_dunder(name=name) or _exempted(node=node, file=file, marker=marker):
                continue
            yield from _violations(node=node, name=name, path=file.path)


def _violations(*, node: Definition, name: str, path: Path) -> Iterator[Violation]:
    if positional := _positional(node=node):
        yield Violation.from_node(
            node=node,
            path=path,
            code=CODE,
            message=f"{name} принимает {', '.join(positional)} по позиции; поставь `*` перед ними",
        )
    if collected := _collectors(node=node):
        yield Violation.from_node(
            node=node,
            path=path,
            code=CODE,
            message=f"{name} принимает {', '.join(collected)}; перечисли аргументы по имени",
        )


def _definitions(*, node: ast.AST, prefix: str = "") -> Iterator[tuple[str, Definition]]:
    """Все функции дерева под именами вида `Класс.метод` или `внешняя.вложенная`."""
    for child in ast.iter_child_nodes(node):
        match child:
            case ast.ClassDef(name=name):
                yield from _definitions(node=child, prefix=f"{prefix}{name}.")
            case ast.FunctionDef(name=name) | ast.AsyncFunctionDef(name=name):
                yield f"{prefix}{name}", child
                yield from _definitions(node=child, prefix=f"{prefix}{name}.")
            case _:
                yield from _definitions(node=child, prefix=prefix)


def _interpreter_dunder(*, name: str) -> bool:
    own = name.rsplit(".", maxsplit=1)[-1]
    if own in OWN_DUNDERS:
        return False
    return own.startswith("__") and own.endswith("__")


def _positional(*, node: Definition) -> tuple[str, ...]:
    """Аргументы, которые вызывающий может передать по позиции."""
    positional = [*node.args.posonlyargs, *node.args.args]
    if positional and positional[0].arg in IMPLICIT:
        positional = positional[1:]
    return tuple(argument.arg for argument in positional)


def _collectors(*, node: Definition) -> tuple[str, ...]:
    """`*args` и `**kwargs` в том виде, в каком их видит вызывающий."""
    stars = ((node.args.vararg, "*"), (node.args.kwarg, "**"))
    return tuple(f"{star}{argument.arg}" for argument, star in stars if argument)


def _exempted(*, node: Definition, file: ParsedFile, marker: str) -> bool:
    """Пометка где угодно в подписи, не только в строке `def`.

    Подпись, растянутая в столбик, несёт пометку на той строке, которой
    заканчивается.
    """
    return any(marker in line for line in _signature_lines(node=node, file=file))


def _signature_lines(*, node: Definition, file: ParsedFile) -> tuple[str, ...]:
    return file.lines[node.lineno - 1 : node.body[0].lineno - 1]
