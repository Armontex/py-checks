"""The names the import contracts are built from."""

from __future__ import annotations

from typing import Final

FILE: Final = ".importlinter"

# The package of the application's modules: layers live both in it and beside it.
MODULES: Final = "modules"

MIGRATIONS: Final = "migrations"

# Only the history is checked: `env.py` beside it is not a migration but the
# code that runs one, and importing the model metadata is part of its job.
VERSIONS: Final = "versions"

SECTION: Final = "contracts"
