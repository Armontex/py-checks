"""Вызов, который принадлежит одному модулю, и больше никому."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from python_checks.checks._location import ZonedSettings, place
from python_checks.checks.database._marker import MARKER
from python_checks.config import CheckSettings
from python_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from python_checks.checks._location import Place
    from python_checks.core import ParsedFile

CODE: Final = "confined-calls"


class Confined(ZonedSettings):
    """Имена методов, зона, где они запрещены, и модуль, который ими владеет.

    `owner` — имя модуля без расширения. Правило его не касается: там вызов и
    должен стоять, потому и владелец.

    `outside` — куски зоны, где правило молчит. Имя метода — всё, что видно по
    одному файлу, и край брокера тому пример: `commit()` у консьюмера
    подтверждает смещение, а не транзакцию базы.
    """

    methods: tuple[str, ...]
    outside: tuple[str, ...] = ()
    owner: str | None = None
    said: str = "этим владеет другой модуль"


class ConfinedCallsSettings(CheckSettings):
    rules: tuple[Confined, ...] = ()


class ConfinedCalls:
    """Падает, если названный метод позвали не там, где ему место.

    Написано ради границы транзакции. Ставка — это одна транзакция: списать
    деньги, записать ставку, записать событие, которое расскажет об этом
    остальной платформе. Репозиторий, коммитящий в середине, превращает её в
    три, и сальдо перестаёт сходиться со ставками. `begin` запрещён рядом с
    `commit` и `rollback` по той же причине с другого конца: вызывающий уже
    открыл транзакцию, а вторая внутри либо падает, либо тихо делает вложенную.

    Имя метода — всё, что видно по одному файлу: чей это объект, сказал бы
    только вывод типов. Поэтому правило и сужено зоной — там, где `commit()`
    может быть только у сессии.

    Настройка: `rules`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = ConfinedCallsSettings
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(
        cls,
        *,
        file: ParsedFile,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        rules = settings_as(
            settings=settings,
            model=ConfinedCallsSettings,
            code=CODE,
        ).rules
        where = place(file=file)
        if where is None:
            return
        listed = [
            rule
            for rule in rules
            if cls._covers(
                rule=rule,
                where=where,
                file=file,
            )
        ]
        if not listed:
            return
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            rule = next((one for one in listed if node.func.attr in one.methods), None)
            if rule is None:
                continue
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                message=f"{ast.unparse(node.func)}: {rule.said}",
            )

    @staticmethod
    def _covers(
        *,
        rule: Confined,
        where: Place,
        file: ParsedFile,
    ) -> bool:
        if rule.owner is not None and file.path.stem == rule.owner:
            return False
        if where.anywhere(zones=rule.outside):
            return False
        return where.anywhere(zones=rule.zones)
