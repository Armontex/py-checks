"""Names every module of the package knows."""

from __future__ import annotations

import re
from typing import Final

SECTION: Final = "translations"

# Where the languages live, one directory each, mirroring the repository.
HOME: Final = "docs/langs"

# The first line of a translation: the hash of the source it was made from.
STAMP: Final = "<!-- sha256:{digest} -->"
STAMPED: Final = re.compile(r"^<!-- sha256:(?P<digest>[0-9a-f]{64}) -->$")
