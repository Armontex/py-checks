"""Все аргументы передаются по имени."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Final

from python_checks.checks.signatures._functions import (
    Definition,
    definitions,
    receiver,
    signature_end,
)
from python_checks.checks.signatures._marker import MARKER
from python_checks.config import CheckSettings
from python_checks.core import Edit, Violation, column

if TYPE_CHECKING:
    from collections.abc import Iterator

    from python_checks.checks.signatures._functions import Function
    from python_checks.core import ParsedFile

CODE: Final = "keyword-only-arguments"

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
    Слово группы `# signature-ok` библиотека тоже понимает.

    Настроек нет.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = CheckSettings
    marker: ClassVar[str] = MARKER

    def run(
        self,
        *,
        file: ParsedFile,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        _ = settings
        for definition in definitions(node=file.tree):
            if self._interpreter_dunder(name=definition.name):
                continue
            yield from self._violations(
                definition=definition,
                file=file,
            )

    @classmethod
    def _violations(
        cls,
        *,
        definition: Definition,
        file: ParsedFile,
    ) -> Iterator[Violation]:
        node, name = definition.node, definition.name
        end_line = signature_end(node=node)
        if positional := cls._positional(definition=definition):
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                message=(
                    f"{name} принимает {', '.join(positional)} по позиции; поставь `*` перед ними"
                ),
                end_line=end_line,
                edit=cls._star(
                    definition=definition,
                    file=file,
                ),
            )
        if collected := cls._collectors(node=node):
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                message=f"{name} принимает {', '.join(collected)}; перечисли аргументы по имени",
                end_line=end_line,
            )

    @staticmethod
    def _interpreter_dunder(*, name: str) -> bool:
        own = name.rsplit(".", maxsplit=1)[-1]
        if own in OWN_DUNDERS:
            return False
        return own.startswith("__") and own.endswith("__")

    @classmethod
    def _positional(cls, *, definition: Definition) -> tuple[str, ...]:
        """Аргументы, которые вызывающий может передать по позиции."""
        skip = receiver(definition=definition)
        arguments = [*definition.node.args.posonlyargs, *definition.node.args.args]
        return tuple(argument.arg for argument in arguments[skip:])

    @staticmethod
    def _collectors(*, node: Function) -> tuple[str, ...]:
        """`*args` и `**kwargs` в том виде, в каком их видит вызывающий."""
        stars = ((node.args.vararg, "*"), (node.args.kwarg, "**"))
        return tuple(f"{star}{argument.arg}" for argument, star in stars if argument)

    @classmethod
    def _star(
        cls,
        *,
        definition: Definition,
        file: ParsedFile,
    ) -> Edit | None:
        """Правка: `*` перед первым аргументом, который сейчас идёт по позиции.

        Не для всех случаев. При `*args` вторая звезда в подписи не встанет, а
        при `/` аргументы позиционны по требованию автора, и снимать его
        требование автофиксу не по чину.
        """
        node = definition.node
        if node.args.vararg is not None or node.args.posonlyargs:
            return None
        first = node.args.args[receiver(definition=definition)]
        line = first.lineno
        at = column(
            line=file.lines[line - 1],
            offset=first.col_offset,
        )
        return Edit(
            line=line,
            column=at,
            end_line=line,
            end_column=at,
            text="*, ",
        )
