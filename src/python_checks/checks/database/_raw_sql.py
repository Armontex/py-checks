"""SQL, написанный строкой там, где хватило бы выражения."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from python_checks.checks._names import name
from python_checks.checks.database._marker import MARKER
from python_checks.config import CheckSettings
from python_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from python_checks.core import ParsedFile

CODE: Final = "raw-sql"

# Вызов — и то, что пишут вместо строки. Каждый берёт SQL первым позиционным.
CALLS: Final[dict[str, str]] = {
    "CheckConstraint": "выражение по колонке, например and_(margin >= NOTHING, margin < WHOLE)",
    "text": "select()/insert(), собранный из атрибутов модели",
    "literal_column": "сама маппед-колонка",
    "column": "сама маппед-колонка",
}


class RawSqlSettings(CheckSettings):
    calls: dict[str, str] = CALLS


class RawSql:
    """Падает, если SQL написан строкой там, где хватило бы выражения.

    CHECK, записанный как `"margin >= 0 AND margin < 1"`, — это второе
    определение правила, которое домен уже сформулировал, на языке, который в
    репозитории никто не проверяет. Переименуй колонку — строка по-прежнему
    компилируется; сдвинь границу — строка по-прежнему называет старое число, и
    расхождение всплывает нарушением ограничения на строке, которая была верна
    по всем правилам, известным коду.

    Записанное выражением — `CheckConstraint(and_(margin >= NOTHING, margin <
    WHOLE))` — оно состоит из атрибута, который pyright и так проверяет, и
    констант, которыми сущность отказывает, так что разъехаться им негде.

    То же про `text()`, `literal_column()` и `column()`: запрос, собранный
    строкой, — запрос, который никто не проверяет, а собранный из значения,
    пришедшего откуда угодно, — инъекция, ждущая забывчивого вызывающего.

    Где выражения честно нет — `SELECT 1` для пробы живости, чтение служебной
    таблицы alembic, — на строке пишут причину:
    `# db-ok: raw-sql: проба живости, формы ORM нет`. Пометка снимается с любой
    строки самого вызова и не достаёт дальше него: пометка на объемлющей
    инструкции извиняет её, а не SQL внутри.

    Миграции правилу не подсудны: миграция — это история, она может не иметь
    права импортировать те самые константы, поэтому её SQL выписан словами и
    заморожен в день рождения. Это `exclude` проекта, а не дело правила.

    Настройка: `calls`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = RawSqlSettings
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(
        cls,
        *,
        file: ParsedFile,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        calls = settings_as(
            settings=settings,
            model=RawSqlSettings,
            code=CODE,
        ).calls
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            written = name(node=node.func)
            if written not in calls or not cls._sql(node=node.args[0]):
                continue
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                # Пометка снимается с любой строки самого вызова.
                end_line=node.end_lineno or node.lineno,
                message=f"{written}(...) со строкой SQL; вместо неё — {calls[written]}",
            )

    @staticmethod
    def _sql(*, node: ast.expr) -> bool:
        """Строковый литерал или строка, собранная из литералов."""
        match node:
            case ast.Constant(value=str()):
                return True
            case ast.JoinedStr() | ast.BinOp(op=ast.Add() | ast.Mod()):
                return any(
                    isinstance(part, ast.Constant) and isinstance(part.value, str)
                    for part in ast.walk(node)
                )
            case _:
                return False
