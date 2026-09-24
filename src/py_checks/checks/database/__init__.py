"""The database.

The transaction boundary, the material of a column, the shape of a statement.
Little of this exists off the shelf: `pytest-alembic` answers for rolling a
migration back, `alembic check` for models and migrations disagreeing, but
somebody has to call it: it needs a live database, which is why
`schema-drift` is declared `ENVIRONMENT`. The rest is the project's own
conventions.
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
