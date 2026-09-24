"""Names and codes shared across the core."""

from __future__ import annotations

from typing import Final

# The entry point group where checks are declared: a check of one's own lives
# in a separate package and needs no fork of the library. There is one group
# for every kind of rule — what a rule is given, a file or the project root,
# it says itself.
GROUP: Final = "py_checks.checks"

# What the shell sees. A bare 1 would be a code whose meaning only the caller
# knows; pre-commit stops the commit on it.
EXIT_OK: Final = 0
EXIT_VIOLATION: Final = 1
