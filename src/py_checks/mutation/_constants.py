"""Names every module of the package knows."""

from __future__ import annotations

from typing import Final

SECTION: Final = "mutation"

# Where `record` writes how many survivors each module has. A file, not a
# number in the settings: a run writes it, and it is not edited by hand.
BASELINE: Final = "mutation-baseline.json"
