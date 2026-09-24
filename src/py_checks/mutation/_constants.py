"""Имена, о которых знают все модули пакета."""

from __future__ import annotations

from typing import Final

SECTION: Final = "mutation"

# Куда `record` пишет, сколько выживших на каждом модуле. Файл, а не число в
# настройках: его пишет прогон, и рукой он не правится.
BASELINE: Final = "mutation-baseline.json"
