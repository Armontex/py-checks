"""A module's functions and what only the tree knows about them."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterator

# The only way for a method not to get its first argument from the interpreter.
STATIC: Final = "staticmethod"

type Function = ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True, slots=True)
class Definition:
    """A function, its name in the form `Class.method`, and whether it is a method.

    The first argument of a method is passed by the interpreter, and the
    author of the signature has nothing to do with it, but that is known by
    position, not by name. `self` in a plain function or in a `@staticmethod`
    is an ordinary argument.
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
    """Every function in the tree, named `Class.method` or `outer.inner`.

    Along the way it remembers whose body is being read: a function in a class
    body is a method, while a function inside a method is not, and nobody
    passes it a first argument.
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
    """How many leading arguments the interpreter passes: one for a method, zero otherwise."""
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
    """The last line of the signature: the mark goes there when the signature is in a column."""
    return max(node.body[0].lineno - 1, node.lineno)
