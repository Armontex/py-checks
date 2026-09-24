"""What a module declares: a class, a port, a dataclass, an alias.

The placement rules speak of kinds of declaration, not of syntax: "`dto/` holds
dataclasses", "`ports/` holds protocols". The kind is recognised once, here,
and every rule of the group uses the same knowledge.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final

from py_checks.checks._names import name, names

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

# A project's exception inherits from its own root (`class NotFound(DomainError)`),
# not from `Exception` — but the root's name ends the same way, and the kind is
# recognised by it without reading another module.
ERROR_SUFFIXES: Final[tuple[str, ...]] = ("Error", "Exception")

# An assignment that declares a name for a type, not a value.
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
    """The kinds of declaration the placement rules speak of."""

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
        """What the kind is called in a message: `str.title` is taken by `str` itself."""
        return NAMES[self]


NAMES: Final[dict[Kind, str]] = {
    Kind.CLASS: "class",
    Kind.PORT: "port",
    Kind.DATACLASS: "dataclass",
    Kind.MODEL: "model",
    Kind.ALIAS: "alias",
    Kind.ENUM: "enum",
    Kind.ERROR: "exception",
    Kind.FUNCTION: "function",
}


@dataclass(frozen=True, slots=True)
class Declaration:
    """A top-level declaration: the name, the kind and the node.

    `kind` is empty when one file does not show the kind: a class with a base
    from another module. Such a class still has a name, and a rule that looks at
    the suffix uses it.
    """

    name: str
    kind: Kind | None
    node: ast.stmt


def declarations(*, tree: ast.Module) -> Iterator[Declaration]:
    """Everything a module declares.

    Imports, constants, `if TYPE_CHECKING` blocks and the docstring are left
    out: they are allowed everywhere, and the placement rules have nothing to
    say about them.
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
    """The class's kind; `None` if one file does not show it.

    A base declared in another module is a kind that cannot be seen from here:
    `class CodeMismatchResponse(ErrorResponse)` is a pydantic model, but that
    can only be learned by reading that module. The rule is silent about such
    a class: the stray helper it was written for usually has no base.
    """
    bases = frozenset(names(nodes=node.bases))
    if bases & ABSTRACT or _metaclass(node=node):
        return Kind.PORT
    if MODEL in bases:
        return Kind.MODEL
    if bases & ENUMS:
        return Kind.ENUM
    if DATACLASS in frozenset(names(nodes=node.decorator_list)):
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
        keyword.arg == "metaclass" and name(node=keyword.value) == ABSTRACT_METACLASS
        for keyword in node.keywords
    )


def _alias(*, node: ast.AnnAssign | ast.Assign) -> bool:
    """An assignment that declares a name for a type.

    Three kinds: annotated with `TypeAlias`, a call of a factory such as
    `NewType`, and a bare `Row = dict[str, int]` — a name for a shape, not a
    value.
    """
    if isinstance(node, ast.AnnAssign) and name(node=node.annotation) == ALIAS_ANNOTATION:
        return True
    if node.value is None:
        return False
    match node.value:
        case ast.Call(func=function):
            return name(node=function) in ALIAS_FACTORIES
        case ast.Subscript(value=value):
            return name(node=value) in ALIAS_CONSTRUCTORS
        case ast.BinOp(op=ast.BitOr()):
            return True
        case _:
            return False
