"""A log line names its event by an enum member, not by a phrase."""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING, ClassVar, Final, Self

from pydantic import model_validator

from py_checks.checks.effects._marker import MARKER
from py_checks.config import CheckSettings
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.core import ParsedFile

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
            message = f"receiver is a regular expression: {broken}"
            raise ValueError(message) from broken
        return self


class LogEvents:
    """Fails if an event in the log is named by something other than an enum member.

    An event's name is not read by a human: a processor in the structlog chain
    turns `consumer.message.handled` into a counter, and an alert joins on that
    string. A literal written at the call site has no definition, and the code
    that EMITS the name is tied to nothing that catches it: a typo breaks no
    test, it simply stops matching, and the metric quietly reads zero.

    The rule reads the SHAPE `LogEvent.SOMETHING` and does not look for the
    member: a name that is not in the enum is refused by pyright, and without
    pyright it is an `AttributeError` on the first run — collecting the members
    would mean catching what is already caught.

    A third-party logger — a library's, or one whose vocabulary another project
    owns — is lifted by a mark: `# effect-ok: log-events: not our logger`.

    Settings: `enum`, `levels`, `receiver`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = LogEventsSettings
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
                    f"an event's name is a member of {limits.enum}, not a phrase; a counter "
                    f"and an alert join on it"
                ),
            )

    @staticmethod
    def _receiver(*, node: ast.expr) -> str:
        """Whose method this is: `logger`, `log`, `self._logger`, `_LOGGER`."""
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
