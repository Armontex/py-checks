"""База данных.

Граница транзакции, материал колонки, форма запроса. Готового тут почти нет:
`alembic check` отвечает на расхождение моделей и миграций, `pytest-alembic` —
на откат, остальное — соглашения проекта.
"""

from python_checks.checks.database._bound_checks import BoundChecks, BoundChecksSettings
from python_checks.checks.database._confined_calls import (
    Confined,
    ConfinedCalls,
    ConfinedCallsSettings,
)
from python_checks.checks.database._marker import MARKER
from python_checks.checks.database._model_boundary import ModelBoundary, ModelBoundarySettings
from python_checks.checks.database._model_columns import ModelColumns, ModelColumnsSettings
from python_checks.checks.database._raw_sql import RawSql, RawSqlSettings
from python_checks.checks.database._statement_keys import StatementKeys, StatementKeysSettings

__all__ = [
    "MARKER",
    "BoundChecks",
    "BoundChecksSettings",
    "Confined",
    "ConfinedCalls",
    "ConfinedCallsSettings",
    "ModelBoundary",
    "ModelBoundarySettings",
    "ModelColumns",
    "ModelColumnsSettings",
    "RawSql",
    "RawSqlSettings",
    "StatementKeys",
    "StatementKeysSettings",
]
