"""Строка лога называет событие членом перечисления, а не фразой."""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING, ClassVar, Final, Self

from pydantic import model_validator

from python_checks.checks.effects._marker import MARKER
from python_checks.config import CheckSettings
from python_checks.core import Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from python_checks.core import ParsedFile

CODE: Final = "log-events"

LEVELS: Final = ("debug", "info", "warning", "warn", "error", "exception", "critical")


class LogEventsSettings(CheckSettings):
    enum: str = "LogEvent"
    levels: tuple[str, ...] = LEVELS
    receiver: str = r"(^|_)log(ger)?$"

    @model_validator(mode="after")
    def _readable(self) -> Self:
        try:
            re.compile(self.receiver)
        except re.error as broken:
            message = f"receiver — регулярное выражение: {broken}"
            raise ValueError(message) from broken
        return self


class LogEvents:
    """Падает, если событие в логе названо чем-то кроме члена перечисления.

    Имя события читает не человек: процессор в цепочке structlog превращает
    `consumer.message.handled` в счётчик, а алерт джойнится по этой строке.
    Литерал, написанный на месте вызова, определения не имеет, и код, который
    имя ИЗДАЁТ, ничем не связан с кодом, который его ловит: опечатка не ломает
    ни одного теста, она просто перестаёт совпадать, и метрика тихо читает
    ноль.

    Правило читает ФОРМУ `LogEvent.SOMETHING` и члена не ищет: имени, которого
    в перечислении нет, pyright откажет, а без него это `AttributeError` на
    первом же запуске — собирать члены значило бы ловить пойманное дважды.

    Чужой логгер — библиотечный или тот, чьим словарём владеет другой проект, —
    снимается пометкой: `# effect-ok: log-events: не наш логгер`.

    Настройки: `enum`, `levels`, `receiver`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = LogEventsSettings
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
            model=LogEventsSettings,
            code=CODE,
        )
        receiver = re.compile(limits.receiver)
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in limits.levels or not node.args:
                continue
            if not receiver.search(cls._receiver(node=node.func.value)):
                continue
            if cls._member(
                node=node.args[0],
                enum=limits.enum,
            ):
                continue
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                message=(
                    f"{ast.unparse(node.func)}({ast.unparse(node.args[0])}...): "
                    f"имя события — член {limits.enum}, а не фраза; по нему джойнятся "
                    f"счётчик и алерт"
                ),
            )

    @staticmethod
    def _receiver(*, node: ast.expr) -> str:
        """Чей это метод: `logger`, `log`, `self._logger`, `_LOGGER`."""
        match node:
            case ast.Name(id=name) | ast.Attribute(attr=name):
                return name
            case _:
                return ""

    @staticmethod
    def _member(
        *,
        node: ast.expr,
        enum: str,
    ) -> bool:
        return (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == enum
        )
