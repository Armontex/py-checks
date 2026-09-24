"""Imports and boundaries.

Layers, module independence and imports in migrations moved to import-linter:
its contracts are built by `py-checks sync`. Two rules stayed here, the ones
that fit a contract inside out — there every place where a package is banned
would have to be listed, and every new one added by hand.

`confined-imports` looks from the side of the package: where it may go.
`sealed-imports` looks from the side of the place: what may come here.

Both tables belong to the project: the library cannot know the names of the
layers or the list of frameworks. Without settings both rules stay silent.
"""

from py_checks.checks.imports._confined import ConfinedImports, ConfinedSettings
from py_checks.checks.imports._marker import MARKER
from py_checks.checks.imports._sealed import SealedImports, SealedSettings

__all__ = [
    "MARKER",
    "ConfinedImports",
    "ConfinedSettings",
    "SealedImports",
    "SealedSettings",
]
