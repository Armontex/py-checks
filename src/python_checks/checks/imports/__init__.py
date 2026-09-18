"""Импорты и границы.

Слои, независимость модулей и импорты в миграциях уехали в import-linter:
контракты для него собирает `python-checks sync`. Здесь остались два правила,
которые в контракты ложатся наизнанку — там пришлось бы перечислять все места,
где пакет запрещён, и дописывать каждое новое.

`confined-imports` смотрит со стороны пакета: где ему можно.
`sealed-imports` — со стороны места: что можно здесь.
"""

from python_checks.checks.imports._base import ALLOW, CONFINED, ZONES
from python_checks.checks.imports._confined import ConfinedImports, ConfinedSettings
from python_checks.checks.imports._marker import MARKER
from python_checks.checks.imports._sealed import SealedImports, SealedSettings

__all__ = [
    "ALLOW",
    "CONFINED",
    "MARKER",
    "ZONES",
    "ConfinedImports",
    "ConfinedSettings",
    "SealedImports",
    "SealedSettings",
]
