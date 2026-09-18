"""Имена, из которых собираются контракты импортов."""

from __future__ import annotations

from typing import Final

FILE: Final = "importlinter.ini"

# Пакет с модулями приложения: слои живут и в нём, и рядом с ним.
MODULES: Final = "modules"

MIGRATIONS: Final = "migrations"

# Проверяется только история: `env.py` рядом — не миграция, а запускающий её
# код, и метаданные моделей он импортирует по своей работе.
VERSIONS: Final = "versions"

SECTION: Final = "contracts"
