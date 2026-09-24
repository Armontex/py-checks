"""Placement and the shape of a module.

Where a class lives, what a directory allows, which class a module must
declare first. These are conventions tied to the directory layout, and no
ready tool covers them: the ArchUnit family for Python is busy with imports,
and pattern engines (Semgrep, ast-grep) can forbid but not permit.

All four rules read one shared `[layout]` table, a block per directory: they
speak about the same thing from four sides, and four tables about one thing
would drift apart. It lives in `checks/_layout.py` because `model-boundary`
reads the same table: the layout is the project's word, not the property of
one group of rules. The table belongs to the project: the library cannot know
names like `use_cases`, `dto` or `schemas`. Without it the rules stay silent.
"""

from py_checks.checks._layout import SECTION, Directory, Layout, Operation, Orm
from py_checks.checks.placement._class_modules import ClassModules
from py_checks.checks.placement._class_placement import ClassPlacement
from py_checks.checks.placement._marker import MARKER
from py_checks.checks.placement._operation_shape import OperationShape, Shape
from py_checks.checks.placement._required_class import RequiredClass

__all__ = [
    "MARKER",
    "SECTION",
    "ClassModules",
    "ClassPlacement",
    "Directory",
    "Layout",
    "Operation",
    "Orm",
    "OperationShape",
    "RequiredClass",
    "Shape",
]
