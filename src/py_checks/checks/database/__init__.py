"""База данных.

Граница транзакции, материал колонки, форма запроса. Готового тут почти нет:
`pytest-alembic` отвечает на откат миграции, `alembic check` — на расхождение
моделей и миграций, но звать его приходится самим: ему нужна живая база,
поэтому `schema-drift` объявлен `ENVIRONMENT`. Остальное — соглашения проекта.
"""

from py_checks.checks.database._bound_checks import BoundChecks, BoundChecksSettings
from py_checks.checks.database._confined_calls import (
    Confined,
    ConfinedCalls,
    ConfinedCallsSettings,
)
from py_checks.checks.database._marker import MARKER
from py_checks.checks.database._model_boundary import ModelBoundary
from py_checks.checks.database._model_columns import ModelColumns, ModelColumnsSettings
from py_checks.checks.database._raw_sql import RawSql, RawSqlSettings
from py_checks.checks.database._schema_drift import SchemaDrift, SchemaDriftSettings
from py_checks.checks.database._statement_keys import StatementKeys, StatementKeysSettings

__all__ = [
    "MARKER",
    "BoundChecks",
    "BoundChecksSettings",
    "Confined",
    "ConfinedCalls",
    "ConfinedCallsSettings",
    "ModelBoundary",
    "ModelColumns",
    "ModelColumnsSettings",
    "RawSql",
    "RawSqlSettings",
    "SchemaDrift",
    "SchemaDriftSettings",
    "StatementKeys",
    "StatementKeysSettings",
]
