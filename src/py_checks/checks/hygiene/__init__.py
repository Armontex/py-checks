"""Repository hygiene.

A dependency declares a ceiling: without one the version is chosen by the
resolver, not by a person. The rest of this group is covered by something
other than checks — `.env.example` is generated from the settings models, and
`CLAUDE.md` is a symlink to `AGENTS.md`.
"""

from py_checks.checks.hygiene._dependency_bounds import (
    DependencyBounds,
    DependencyBoundsSettings,
)
from py_checks.checks.hygiene._marker import MARKER

__all__ = ["MARKER", "DependencyBounds", "DependencyBoundsSettings"]
