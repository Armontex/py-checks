"""API and events.

An entrance into the process declares in its decorator everything that was
decided for it: the framework has the mechanism but does not demand it, and
each of its defaults is a decision made by somebody other than this project.
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
