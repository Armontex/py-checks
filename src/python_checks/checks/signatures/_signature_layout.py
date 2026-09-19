"""Список из двух и более элементов пишется в столбик."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from python_checks.checks.signatures._functions import definitions, receiver
from python_checks.checks.signatures._marker import MARKER
from python_checks.config import CheckSettings
from python_checks.core import Edit, Scope, Violation, column, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from python_checks.checks.signatures._functions import Definition, Function
    from python_checks.core import ParsedFile

CODE: Final = "signature-layout"

# Двух элементов достаточно: один в строке читается как одно слово, а два уже
# приходится разбирать.
ENOUGH: Final = 2


class SignatureLayoutSettings(CheckSettings):
    calls: bool = True


class SignatureLayout:
    """Падает, если список из двух и более элементов записан в одну строку.

    Обе половины вызова: подпись, которая объявляет параметры, и место, которое
    их передаёт. В столбике правка одного аргумента трогает одну строку и
    говорит ровно это; тот же список в строку сдвигает всё, что стоит после
    правки, и ревью читает его целиком, чтобы найти изменение. В вызове это
    важнее, чем в подписи: там стоят выражения, а не имена.

    `self` и `cls` не в счёт — их передаёт интерпретатор.

    В вызове правило срабатывает от двух и более ИМЕНОВАННЫХ аргументов, и это
    вся граница между своим кодом и чужим: у нас каждая функция keyword-only,
    поэтому вызов нашей функции — сплошь имена и под правило попадает, а
    `isinstance(node, ast.Call)` и `range(1, 10)` — чужая позиционная подпись, и
    её не трогают. Как только сработало, в столбик идут все аргументы,
    позиционные тоже: наполовину развёрнутый вызов правилу ни к чему.

    Декоратор — единственное исключение: `@dataclass(frozen=True, slots=True)`
    это метка, а не список, который читают ради смысла. Те же слова на каждом
    dataclass сервиса, переставлять там нечего.

    `--fix` дописывает висячую запятую и зовёт `ruff format`: форматтер держит
    список в столбик, когда запятая стоит, но сам её никогда не ставит.

    Настройка: `calls` — судить ли места вызова. Половина правила про вызовы
    дороже половины про подписи: в сервисе, который писали без неё, она трогает
    почти каждый файл, и выключить её на время переезда честнее, чем выключить
    правило целиком.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = SignatureLayoutSettings
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(
        cls,
        *,
        file: ParsedFile,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        calls = settings_as(
            settings=settings,
            model=SignatureLayoutSettings,
            code=CODE,
        ).calls
        for definition in definitions(node=file.tree):
            yield from cls._signature(
                file=file,
                definition=definition,
            )
        if not calls:
            return
        marks = cls._decorators(tree=file.tree)
        for node in ast.walk(file.tree):
            if isinstance(node, ast.Call) and id(node) not in marks:
                yield from cls._call(
                    file=file,
                    node=node,
                )

    @classmethod
    def _signature(
        cls,
        *,
        file: ParsedFile,
        definition: Definition,
    ) -> Iterator[Violation]:
        node = definition.node
        listed = cls._parameters(definition=definition)
        defaults = cls._defaults(node=node)
        if len(listed) < ENOUGH or cls._columned(
            listed=listed,
            after=node.lineno,
        ):
            return
        yield Violation.from_node(
            node=node,
            path=file.path,
            code=CODE,
            message=(
                f"{definition.name}: параметров {len(listed)} в одну строку; по одному на строку"
            ),
            edit=cls._comma(
                file=file,
                ends=[*cls._ends(nodes=listed), *cls._ends(nodes=defaults)],
            ),
        )

    @classmethod
    def _call(
        cls,
        *,
        file: ParsedFile,
        node: ast.Call,
    ) -> Iterator[Violation]:
        listed: list[ast.expr | ast.keyword] = [*node.args, *node.keywords]
        if len(node.keywords) < ENOUGH:
            return
        after = node.func.end_lineno or node.func.lineno
        if cls._columned(
            listed=listed,
            after=after,
        ):
            return
        yield Violation.from_node(
            node=node,
            path=file.path,
            code=CODE,
            message=(
                f"{cls._called(node=node)}: аргументов {len(listed)} в одну строку; "
                f"по одному на строку"
            ),
            edit=cls._comma(
                file=file,
                ends=cls._ends(nodes=listed),
            ),
        )

    @staticmethod
    def _columned(
        *,
        listed: Sequence[ast.expr | ast.keyword | ast.arg],
        after: int,
    ) -> bool:
        """По одному на строку, и ни одного на той строке, где список открылся."""
        lines = {element.lineno for element in listed}
        return len(lines) == len(listed) and min(lines) > after

    @staticmethod
    def _parameters(*, definition: Definition) -> list[ast.arg]:
        """Параметры, которые заполняет вызывающий, в порядке записи."""
        arguments = definition.node.args
        listed = [
            *arguments.posonlyargs,
            *arguments.args,
            *([arguments.vararg] if arguments.vararg else []),
            *arguments.kwonlyargs,
            *([arguments.kwarg] if arguments.kwarg else []),
        ]
        return listed[receiver(definition=definition) :]

    @staticmethod
    def _defaults(*, node: Function) -> list[ast.expr]:
        """Значения по умолчанию: запятая ставится после них, а не после имени."""
        return [one for one in (*node.args.defaults, *node.args.kw_defaults) if one is not None]

    @staticmethod
    def _ends(*, nodes: Sequence[ast.expr | ast.keyword | ast.arg]) -> list[tuple[int, int]]:
        """Где кончается каждый элемент списка."""
        return [
            (node.end_lineno, node.end_col_offset)
            for node in nodes
            if node.end_lineno is not None and node.end_col_offset is not None
        ]

    @staticmethod
    def _comma(
        *,
        file: ParsedFile,
        ends: list[tuple[int, int]],
    ) -> Edit | None:
        """Правка: висячая запятая после последнего элемента списка.

        Последний — по концу, а не по порядку записи: у параметра со значением
        по умолчанию запятая ставится после значения, а не после имени.

        Дальше раскладка — забота форматтера: `ruff format` разворачивает
        список в столбик, как только запятая стоит.
        """
        if not ends:
            return None
        line, offset = max(ends)
        at = column(
            line=file.lines[line - 1],
            offset=offset,
        )
        return Edit(
            line=line,
            column=at,
            end_line=line,
            end_column=at,
            text=",",
        )

    @staticmethod
    def _called(*, node: ast.Call) -> str:
        """Как вызов записан: `self._policy`, `price`, `Model.build`."""
        return ast.unparse(node.func)

    @staticmethod
    def _decorators(*, tree: ast.Module) -> frozenset[int]:
        """Вызовы, которые на самом деле декораторы, — по тождеству узла."""
        return frozenset(
            id(decorator)
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
            for decorator in node.decorator_list
            if isinstance(decorator, ast.Call)
        )
