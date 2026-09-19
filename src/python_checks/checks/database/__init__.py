"""База данных.

Граница транзакции, материал колонки, форма запроса. Готового тут почти нет:
`alembic check` отвечает на расхождение моделей и миграций, `pytest-alembic` —
на откат, остальное — соглашения проекта.
"""

from python_checks.checks.database._confined_calls import (
    Confined,
    ConfinedCalls,
    ConfinedCallsSettings,
)
from python_checks.checks.database._marker import MARKER

__all__ = [
    "MARKER",
    "Confined",
    "ConfinedCalls",
    "ConfinedCallsSettings",
]
