"""Import contracts for import-linter.

What the layers are called and who may import what is known to the project,
not the library: in a service it is `domain` and `presentation`, in a utility
`core` and `cli`, and there is no guessing it on their behalf. The project
states it in `[tool.py-checks.contracts]`, and `py-checks sync` builds the
contracts for its layout: layers that are not on disk stay out of the file,
otherwise import-linter would fail on the first module that does not exist.

There is nothing to edit in the built file — the next sync overwrites it; the
section is what changes.
"""

from py_checks.contracts._constants import FILE, MIGRATIONS, MODULES, SECTION
from py_checks.contracts._render import render
from py_checks.contracts._settings import Contracts, contracts

__all__ = [
    "FILE",
    "MIGRATIONS",
    "MODULES",
    "SECTION",
    "Contracts",
    "contracts",
    "render",
]
