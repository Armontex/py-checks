"""A file's imports in the form the rules talk about them."""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterator

STDLIB: Final[frozenset[str]] = frozenset(sys.stdlib_module_names)


@dataclass(frozen=True, slots=True)
class Imported:
    """One import: the node, the full name and the package it belongs to."""

    node: ast.stmt
    module: str

    @property
    def top(self) -> str:
        return self.module.split(".", maxsplit=1)[0]

    @property
    def stdlib(self) -> bool:
        return self.top in STDLIB


def imports(*, tree: ast.Module) -> Iterator[Imported]:
    """Every import of the module except relative ones.

    A relative import is always a neighbour in the same package, that is, the
    project's own code: to rules about foreign packages it means nothing.
    """
    for node in ast.walk(tree):
        match node:
            case ast.Import(names=names):
                for name in names:
                    yield Imported(
                        node=node,
                        module=name.name,
                    )
            case ast.ImportFrom(module=str(module), level=0):
                yield Imported(
                    node=node,
                    module=module,
                )
            case _:
                continue
