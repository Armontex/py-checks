"""Все аргументы передаются по имени."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Final

from python_checks.checks.signatures._marker import MARKER
from python_checks.config import CheckSettings
from python_checks.core import Edit, Violation

if TYPE_CHECKING:
    from collections.abc import Iterator

    from python_checks.core import ParsedFile

CODE: Final = "keyword-only-arguments"

type Function = ast.FunctionDef | ast.AsyncFunctionDef

# Единственный способ для метода не получить первый аргумент от интерпретатора.
STATIC: Final = "staticmethod"

# Дандеры, которые зовёт наш собственный код: их вызов — такой же вызов, как
# любой другой. Остальные дандеры зовёт интерпретатор, и подпись у них не наша.
OWN_DUNDERS: Final[frozenset[str]] = frozenset({"__init__", "__new__", "__call__"})


@dataclass(frozen=True, slots=True)
class Definition:
    """Функция и то, что о ней знает только дерево.

    Первый аргумент метода передаёт интерпретатор, и автор подписи тут ни при
    чём — но узнаётся это по месту, а не по имени. `self` в обычной функции или
    в `@staticmethod` — обычный аргумент, и спрашивать его по позиции нельзя.
    """

    name: str
    node: Function
    method: bool


class KeywordOnlyArguments:
    """Падает, если подпись записана не полностью.

    Каждый аргумент передаётся по имени, поэтому место вызова читается как
    документация, а аргументы можно менять местами, не ломая вызовы:

        def price(*, market: Market, stake: Money) -> Money: ...

    `*args` и `**kwargs` запрещены по той же причине: сборщик принимает что
    угодно, проверять типы там нечего, а место вызова ничего не объясняет. Их
    `--fix` не трогает: имена аргументов вместо звёздочек придумывает автор.

    Обратный вызов или обёртка, чью подпись диктует библиотека, помечается в
    подписи: `def f(a): ...  # check-ok: keyword-only-arguments: sqlalchemy`.
    Старое слово `# signature-ok` библиотека тоже понимает.

    Настроек нет.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = CheckSettings
    marker: ClassVar[str] = MARKER

    def run(self, *, file: ParsedFile, settings: CheckSettings) -> Iterator[Violation]:
        _ = settings
        for definition in _definitions(node=file.tree):
            if _interpreter_dunder(name=definition.name):
                continue
            yield from _violations(definition=definition, file=file)


def _violations(*, definition: Definition, file: ParsedFile) -> Iterator[Violation]:
    node, name = definition.node, definition.name
    end_line = _signature_end(node=node)
    if positional := _positional(definition=definition):
        yield Violation.from_node(
            node=node,
            path=file.path,
            code=CODE,
            message=f"{name} принимает {', '.join(positional)} по позиции; поставь `*` перед ними",
            end_line=end_line,
            edit=_star(definition=definition),
        )
    if collected := _collectors(node=node):
        yield Violation.from_node(
            node=node,
            path=file.path,
            code=CODE,
            message=f"{name} принимает {', '.join(collected)}; перечисли аргументы по имени",
            end_line=end_line,
        )


def _definitions(*, node: ast.AST, prefix: str = "", method: bool = False) -> Iterator[Definition]:
    """Все функции дерева под именами вида `Класс.метод` или `внешняя.вложенная`.

    Заодно запоминается, тело какого узла мы разбираем: функция в теле класса —
    метод, а функция внутри метода — уже нет, и первый аргумент ей никто не
    передаёт.
    """
    for child in ast.iter_child_nodes(node):
        match child:
            case ast.ClassDef(name=name):
                yield from _definitions(node=child, prefix=f"{prefix}{name}.", method=True)
            case ast.FunctionDef(name=name) | ast.AsyncFunctionDef(name=name):
                yield Definition(name=f"{prefix}{name}", node=child, method=method)
                yield from _definitions(node=child, prefix=f"{prefix}{name}.", method=False)
            case _:
                yield from _definitions(node=child, prefix=prefix, method=method)


def _interpreter_dunder(*, name: str) -> bool:
    own = name.rsplit(".", maxsplit=1)[-1]
    if own in OWN_DUNDERS:
        return False
    return own.startswith("__") and own.endswith("__")


def _positional(*, definition: Definition) -> tuple[str, ...]:
    """Аргументы, которые вызывающий может передать по позиции."""
    arguments = [*definition.node.args.posonlyargs, *definition.node.args.args]
    return tuple(argument.arg for argument in arguments[_receiver(definition=definition) :])


def _receiver(*, definition: Definition) -> int:
    """Сколько первых аргументов передаёт интерпретатор: один у метода, иначе ноль."""
    if not definition.method or _static(node=definition.node):
        return 0
    return 1


def _static(*, node: Function) -> bool:
    return STATIC in tuple(_decorator(node=item) for item in node.decorator_list)


def _decorator(*, node: ast.expr) -> str:
    match node:
        case ast.Name(id=name) | ast.Attribute(attr=name):
            return name
        case _:
            return ""


def _collectors(*, node: Function) -> tuple[str, ...]:
    """`*args` и `**kwargs` в том виде, в каком их видит вызывающий."""
    stars = ((node.args.vararg, "*"), (node.args.kwarg, "**"))
    return tuple(f"{star}{argument.arg}" for argument, star in stars if argument)


def _star(*, definition: Definition) -> Edit | None:
    """Правка: `*` перед первым аргументом, который сейчас идёт по позиции.

    Не для всех случаев. При `*args` вторая звезда в подписи не встанет, а при
    `/` аргументы позиционны по требованию автора, и снимать его требование
    автофиксу не по чину.
    """
    node = definition.node
    if node.args.vararg is not None or node.args.posonlyargs:
        return None
    first = node.args.args[_receiver(definition=definition)]
    line, column = first.lineno, first.col_offset + 1
    return Edit(line=line, column=column, end_line=line, end_column=column, text="*, ")


def _signature_end(*, node: Function) -> int:
    """Последняя строка подписи: на ней стоит маркер, если подпись в столбик."""
    return max(node.body[0].lineno - 1, node.lineno)
