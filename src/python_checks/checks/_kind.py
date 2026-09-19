"""Что объявлено в модуле: класс, порт, dataclass, алиас.

Правила размещения говорят о видах объявлений, а не о синтаксисе: «в `dto/`
лежат dataclass-ы», «в `ports/` — протоколы». Вид узнаётся один раз здесь, и
этим же знанием пользуются все правила группы.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterator

ABSTRACT: Final[frozenset[str]] = frozenset({"Protocol", "ABC"})
ABSTRACT_METACLASS: Final = "ABCMeta"
MODEL: Final = "BaseModel"
DATACLASS: Final = "dataclass"
ENUMS: Final[frozenset[str]] = frozenset(
    {"Enum", "StrEnum", "IntEnum", "Flag", "IntFlag", "ReprEnum"}
)

ERROR_BASES: Final[frozenset[str]] = frozenset({"Exception", "BaseException"})

# Исключение проекта наследуется от своего же корня (`class NotFound(DomainError)`),
# а не от `Exception`, — но имя корня кончается так же, и по нему вид узнаётся,
# не читая чужой модуль.
ERROR_SUFFIXES: Final[tuple[str, ...]] = ("Error", "Exception")

# Присваивание, которым объявляют имя для типа, а не значение.
ALIAS_ANNOTATION: Final = "TypeAlias"
ALIAS_FACTORIES: Final[frozenset[str]] = frozenset(
    {"TypeVar", "NewType", "ParamSpec", "TypeAliasType"},
)
ALIAS_CONSTRUCTORS: Final[frozenset[str]] = frozenset(
    {
        "dict",
        "list",
        "set",
        "tuple",
        "frozenset",
        "type",
        "Union",
        "Optional",
        "Literal",
        "Callable",
    },
)


class Kind(StrEnum):
    """Виды объявлений, о которых говорят правила размещения."""

    CLASS = "class"
    PORT = "port"
    DATACLASS = "dataclass"
    MODEL = "model"
    ALIAS = "alias"
    ENUM = "enum"
    ERROR = "error"
    FUNCTION = "function"

    @property
    def said(self) -> str:
        """Как вид называется в сообщении: `str.title` занят самим `str`."""
        return NAMES[self]


NAMES: Final[dict[Kind, str]] = {
    Kind.CLASS: "класс",
    Kind.PORT: "порт",
    Kind.DATACLASS: "dataclass",
    Kind.MODEL: "модель",
    Kind.ALIAS: "алиас",
    Kind.ENUM: "перечисление",
    Kind.ERROR: "исключение",
    Kind.FUNCTION: "функция",
}


@dataclass(frozen=True, slots=True)
class Declaration:
    """Объявление верхнего уровня: имя, вид и узел.

    `kind` пуст, когда вид по одному файлу не виден: класс с базой из другого
    модуля. Имя у такого всё равно есть, и правило, которое смотрит на суффикс,
    им пользуется.
    """

    name: str
    kind: Kind | None
    node: ast.stmt


def declarations(*, tree: ast.Module) -> Iterator[Declaration]:
    """Всё, что модуль объявляет.

    Импорты, константы, блоки `if TYPE_CHECKING` и докстринг сюда не попадают:
    они разрешены везде, и правилам размещения о них говорить нечего.
    """
    for node in tree.body:
        match node:
            case ast.ClassDef(name=name):
                yield Declaration(
                    name=name,
                    kind=_class(node=node),
                    node=node,
                )
            case ast.FunctionDef(name=name) | ast.AsyncFunctionDef(name=name):
                yield Declaration(
                    name=name,
                    kind=Kind.FUNCTION,
                    node=node,
                )
            case ast.AnnAssign(target=ast.Name(id=name)) | ast.Assign(targets=[ast.Name(id=name)]):
                if _alias(node=node):
                    yield Declaration(
                        name=name,
                        kind=Kind.ALIAS,
                        node=node,
                    )
            case _:
                continue


def _class(*, node: ast.ClassDef) -> Kind | None:
    """Вид класса; `None`, если по одному файлу его не видно.

    База, объявленная в другом модуле, — это вид, которого отсюда не видно:
    `class CodeMismatchResponse(ErrorResponse)` — pydantic-модель, но узнать
    это можно только прочитав тот модуль. Про такой класс правило молчит:
    заблудившийся хелпер, ради которого оно написано, базы обычно не имеет.
    """
    bases = frozenset(_names(nodes=node.bases))
    if bases & ABSTRACT or _metaclass(node=node):
        return Kind.PORT
    if MODEL in bases:
        return Kind.MODEL
    if bases & ENUMS:
        return Kind.ENUM
    if DATACLASS in frozenset(_names(nodes=node.decorator_list)):
        return Kind.DATACLASS
    if _error(bases=bases):
        return Kind.ERROR
    if bases:
        return None
    return Kind.CLASS


def _error(*, bases: frozenset[str]) -> bool:
    return bool(bases & ERROR_BASES) or any(base.endswith(ERROR_SUFFIXES) for base in bases)


def _metaclass(*, node: ast.ClassDef) -> bool:
    return any(
        keyword.arg == "metaclass" and _name(node=keyword.value) == ABSTRACT_METACLASS
        for keyword in node.keywords
    )


def _alias(*, node: ast.AnnAssign | ast.Assign) -> bool:
    """Присваивание, объявляющее имя для типа.

    Три вида: с аннотацией `TypeAlias`, вызов фабрики вроде `NewType`, и голое
    `Row = dict[str, int]` — имя для формы, а не значение.
    """
    if isinstance(node, ast.AnnAssign) and _name(node=node.annotation) == ALIAS_ANNOTATION:
        return True
    if node.value is None:
        return False
    match node.value:
        case ast.Call(func=function):
            return _name(node=function) in ALIAS_FACTORIES
        case ast.Subscript(value=value):
            return _name(node=value) in ALIAS_CONSTRUCTORS
        case ast.BinOp(op=ast.BitOr()):
            return True
        case _:
            return False


def _names(*, nodes: list[ast.expr]) -> Iterator[str]:
    for node in nodes:
        base = node.value if isinstance(node, ast.Subscript) else node
        if (name := _name(node=base)) is not None:
            yield name


def _name(*, node: ast.expr) -> str | None:
    match node:
        case ast.Name(id=name) | ast.Attribute(attr=name):
            return name
        case ast.Call(func=function):
            return _name(node=function)
        case _:
            return None
