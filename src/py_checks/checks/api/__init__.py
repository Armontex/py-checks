"""API и события.

Вход в процесс объявляет в декораторе всё, что за него решили: механизм у
фреймворка есть, требования писать — нет, а каждое его умолчание — решение,
принятое не этим проектом.
"""

from py_checks.checks.api._edge_declarations import (
    KNOWN,
    Edge,
    EdgeDeclarations,
    Edges,
    Framework,
    Shape,
)
from py_checks.checks.api._marker import MARKER

__all__ = ["KNOWN", "MARKER", "Edge", "EdgeDeclarations", "Edges", "Framework", "Shape"]
