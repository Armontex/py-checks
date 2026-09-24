"""The length of a function."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Final

from pydantic import Field

from py_checks.checks.signatures._functions import definitions, signature_end
from py_checks.checks.signatures._marker import MARKER
from py_checks.config import CheckSettings
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.checks.signatures._functions import Definition
    from py_checks.core import ParsedFile

CODE: Final = "function-length"


class FunctionLengthSettings(CheckSettings):
    max_lines: int = Field(
        default=50,
        gt=0,
    )


class FunctionLength:
    """Fails when a function is longer than the limit.

    A function over the limit hides a second one inside it. The body is
    counted as written, since blank lines and comments are held in the head
    too, but the signature and decorators are not: they describe the function,
    not the work it does.

    Ruff has a similar rule, `PLR0915`, but it counts statements, not lines:
    measured on four services, it fired zero times at a limit of fifty, and
    the longest function there is 91 lines and two statements.

    Settings: `max-lines`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = FunctionLengthSettings
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
            model=FunctionLengthSettings,
            code=CODE,
        )
        for definition in definitions(node=file.tree):
            length = cls._length(definition=definition)
            if length <= limits.max_lines:
                continue
            yield Violation.from_node(
                node=definition.node,
                path=file.path,
                code=CODE,
                # The mark belongs at the end of the signature: it does not
                # always fit on the `def` line, and a signature laid out in a
                # column ends far from where the violation points.
                end_line=signature_end(node=definition.node),
                message=(
                    f"{definition.name}: {length} lines, the limit is {limits.max_lines}; "
                    "move part of it into a separate function"
                ),
            )

    @staticmethod
    def _length(*, definition: Definition) -> int:
        """The body's lines: from the first statement to the function's last line.

        The signature is not counted: laid out in a column, it would add a
        dozen lines to the function that nobody reads as work.
        """
        node = definition.node
        end = node.end_lineno
        if end is None:
            return 0
        return end - node.body[0].lineno + 1
