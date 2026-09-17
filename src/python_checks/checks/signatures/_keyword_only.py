"""Все аргументы передаются по имени."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from python_checks.config import CheckSettings
from python_checks.core import Edit, Violation

if TYPE_CHECKING:
    from collections.abc import Iterator

    from python_checks.core import ParsedFile

CODE: Final = "keyword-only-arguments"

type Definition = ast.FunctionDef | ast.AsyncFunctionDef

# Передаются интерпретатором позиционно, автор подписи тут ни при чём.
IMPLICIT: Final[frozenset[str]] = frozenset({"self", "cls"})

# Дандеры, которые зовёт наш собственный код: их вызов — такой же вызов, как
# любой другой. Остальные дандеры зовёт интерпретатор, и подпись у них не наша.
OWN_DUNDERS: Final[frozenset[str]] = frozenset({"__init__", "__new__", "__call__"})


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
    marker: ClassVar[str | None] = "# signature-ok"

    def run(self, *, file: ParsedFile, settings: CheckSettings) -> Iterator[Violation]:
        _ = settings
        for name, node in _definitions(node=file.tree):
            if _interpreter_dunder(name=name):
                continue
            yield from _violations(node=node, name=name, file=file)


def _violations(*, node: Definition, name: str, file: ParsedFile) -> Iterator[Violation]:
    end_line = _signature_end(node=node)
    if positional := _positional(node=node):
        yield Violation.from_node(
            node=node,
            path=file.path,
            code=CODE,
            message=f"{name} принимает {', '.join(positional)} по позиции; поставь `*` перед ними",
            end_line=end_line,
            edit=_star(node=node),
        )
    if collected := _collectors(node=node):
        yield Violation.from_node(
            node=node,
            path=file.path,
            code=CODE,
            message=f"{name} принимает {', '.join(collected)}; перечисли аргументы по имени",
            end_line=end_line,
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


def _star(*, node: Definition) -> Edit | None:
    """Правка: `*` перед первым аргументом, который сейчас идёт по позиции.

    Не для всех случаев. При `*args` вторая звезда в подписи не встанет, а при
    `/` аргументы позиционны по требованию автора, и снимать его требование
    автофиксу не по чину.
    """
    if node.args.vararg is not None or node.args.posonlyargs:
        return None
    first = node.args.args[0]
    if first.arg in IMPLICIT:
        first = node.args.args[1]
    line, column = first.lineno, first.col_offset + 1
    return Edit(line=line, column=column, end_line=line, end_column=column, text="*, ")


def _signature_end(*, node: Definition) -> int:
    """Последняя строка подписи: на ней стоит маркер, если подпись в столбик."""
    return max(node.body[0].lineno - 1, node.lineno)
