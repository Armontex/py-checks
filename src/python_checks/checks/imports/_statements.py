"""Импорты файла в том виде, в каком о них говорят правила."""

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
    """Один импорт: узел, полное имя и пакет, которому оно принадлежит."""

    node: ast.stmt
    module: str

    @property
    def top(self) -> str:
        return self.module.split(".", maxsplit=1)[0]

    @property
    def stdlib(self) -> bool:
        return self.top in STDLIB


def imports(*, tree: ast.Module) -> Iterator[Imported]:
    """Все импорты модуля, кроме относительных.

    Относительный импорт — это всегда сосед по пакету, то есть код самого
    проекта: для правил про чужие пакеты он ничего не значит.
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
