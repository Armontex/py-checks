"""Names: how they are read in the tree and matched against the settings.

Rules speak in names: "the base is called `Base`", "this column is declared
with `mapped_column`", "`datetime.now` is taken as a port". Asking a node what
it is called is not every rule's business: there is one way per language, and
it lives here.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

DOT: Final = "."
ANY: Final = "*"


def name(*, node: ast.expr) -> str:
    """What this is called; an empty string if it cannot be called by a name.

    A string annotation (`-> "Order"`) is a name spelled out in letters: there
    is no reason to tell it from an ordinary one, the author meant the same
    thing. A call and a subscript, though, do not count as names:
    `tuple(...)[:1]` is a slice of a list, and a rule about type shapes must not
    take it for a declaration. Unwrapping them is asked for by whoever reads
    bases and decorators — `names`.
    """
    match node:
        case ast.Name(id=found) | ast.Attribute(attr=found) | ast.Constant(value=str() as found):
            return found
        case _:
            return ""


def names(*, nodes: Iterable[ast.expr]) -> Iterator[str]:
    """The names of what is listed: a class's bases, decorators.

    Here the name really does stand behind a call and a subscript:
    `@dataclass(frozen=True)` is `dataclass`, `Generic[T]` is `Generic`.
    """
    for node in nodes:
        if found := name(node=_head(node=node)):
            yield found


def _head(*, node: ast.expr) -> ast.expr:
    """What an expression is made of: what it started from before calls and subscripts."""
    match node:
        case ast.Call(func=inner) | ast.Subscript(value=inner):
            return _head(node=inner)
        case _:
            return node


def walked(*, node: ast.expr) -> Iterator[str]:
    """Every name inside an expression, at any depth and in written order.

    `dict[str, Order | None]` is `dict`, `str`, `Order`: a rule about
    annotations looks at what is named in one, not at its shape. A name in
    quotes is the same name: a forward reference is written as a string not
    for meaning, but because the class does not exist yet at that point.
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
    """The tail of a name: `datetime.now` is also `datetime.datetime.now`.

    `random.*` matches any call of the whole module: what matters is not the
    last part but what it was taken from.
    """
    parts = called.split(DOT)
    wanted = pattern.split(DOT)
    if wanted[-1] == ANY:
        head = wanted[:-1]
        return len(parts) > len(head) and parts[-len(head) - 1 : -1] == head
    return len(parts) >= len(wanted) and parts[-len(wanted) :] == wanted
