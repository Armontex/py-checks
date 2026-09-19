"""У некоторых функций законных мест вызова ровно столько, сколько перечислено."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks._location import place
from py_checks.checks._names import matches
from py_checks.checks.calls._marker import MARKER
from py_checks.config import CheckSettings
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.core import ParsedFile

CODE: Final = "confined-functions"


class ConfinedFunctionsSettings(CheckSettings):
    calls: dict[str, tuple[str, ...]] = {}  # noqa: RUF012 — pydantic копирует значение сам
    home: str | None = None


class ConfinedFunctions:
    """Падает, если названная функция позвана не оттуда, откуда ей можно.

    Написано ради конверсии денег. Сервис считает в одной валюте, и гарантия
    за этой фразой — не имя типа: это то, что у конверсии одна реализация и
    места её вызова можно перечислить. Где угодно ещё конверсия — это сумма в
    чьей-то валюте посреди расчёта, и ошибка, которую она даёт, — число,
    верное ровно до того дня, когда встретятся две валюты.

    Место — кусок пути, а не файл: край — это место в замысле, и файл, который
    разделили надвое, краем быть не перестал.

    `home` — модуль, где функция объявлена: там она написана, а не позвана, и
    правило его не трогает.

    Настройки: `calls`, `home`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = ConfinedFunctionsSettings
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(
        cls,
        *,
        file: ParsedFile,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        limits = settings_as(
            settings=settings,
            model=ConfinedFunctionsSettings,
            code=CODE,
        )
        where = place(file=file)
        if where is None or not limits.calls:
            return
        if limits.home is not None and where.holds(path=limits.home):
            return
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.Call):
                continue
            called = ast.unparse(node.func)
            allowed = cls._allowed(
                called=called,
                calls=limits.calls,
            )
            if allowed is None or where.anywhere(
                zones=allowed,
            ):
                continue
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                message=f"{called}() зовут не отсюда; её места — {', '.join(allowed)}",
            )

    @staticmethod
    def _allowed(
        *,
        called: str,
        calls: dict[str, tuple[str, ...]],
    ) -> tuple[str, ...] | None:
        return next(
            (
                zones
                for pattern, zones in calls.items()
                if matches(
                    called=called,
                    pattern=pattern,
                )
            ),
            None,
        )
