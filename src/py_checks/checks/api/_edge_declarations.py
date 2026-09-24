"""An entrance into the process declares in its decorator everything decided for it."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import StrEnum
from http import HTTPStatus
from typing import TYPE_CHECKING, ClassVar, Final, Self

from pydantic import model_validator

from py_checks.checks.api._marker import MARKER
from py_checks.config import OPEN, CheckSettings
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.core import ParsedFile

CODE: Final = "edge-declarations"

STATUS: Final = "status_code"


class Framework(StrEnum):
    """The framework an entrance is written with."""

    FASTAPI = "fastapi"
    FASTSTREAM = "faststream"


@dataclass(frozen=True, slots=True)
class Shape:
    """How a framework writes an entrance. This is the library's knowledge, not the project's.

    The project decides what an entrance must declare; what an "entrance" is
    in FastAPI and in FastStream was decided by their authors, and a table the
    project wrote about it would be a retelling of somebody else's
    documentation, going stale along with it.
    """

    # The method names an entrance is declared with: `broker.subscriber`,
    # `router.post`. The object name on the left is not read — it is a variable
    # name, and a rule about what a variable is called would be a rule about
    # spelling.
    methods: tuple[str, ...]

    # Only as a decorator. For a route this is a must: its `methods` are `get`,
    # `post`, `delete`, the same names an HTTP client goes by, and a rule
    # reading every `.post(...)` would find a route in the first adapter that
    # talks to a neighbouring service. A subscription cannot be mistaken for
    # anything like that, and it is written both as a decorator and as a call:
    # it is kept in a variable and applied to the handler separately, because
    # its client is taken before the start.
    decorated: bool

    # The word a message uses for the first argument.
    subject: str

    # The first argument's name if it is written by keyword; `None` — positional.
    named: str | None

    # The argument declaring the response body, and the statuses that never have one.
    body: str | None = None
    bodiless: tuple[int, ...] = ()

    # The flag an entrance uses to say it is not in the schema.
    exempt: str | None = None


KNOWN: Final[dict[str, Shape]] = {
    Framework.FASTAPI: Shape(
        methods=("get", "post", "put", "patch", "delete", "head", "options", "trace"),
        decorated=True,
        subject="path",
        named="path",
        body="response_model",
        bodiless=(
            int(HTTPStatus.NO_CONTENT),
            int(HTTPStatus.RESET_CONTENT),
            int(HTTPStatus.NOT_MODIFIED),
        ),
        exempt="include_in_schema",
    ),
    Framework.FASTSTREAM: Shape(
        methods=("subscriber",),
        decorated=False,
        subject="topic",
        named=None,
    ),
}


class Edge(CheckSettings):
    """What an entrance of this framework must name.

    Every name here is a decision that has a default in the framework's
    library, and that default was made by somebody other than whoever writes
    the service.
    """

    required: tuple[str, ...] = ()


class Edges(CheckSettings):
    """The entrance table: one block per framework.

    ```toml
    [edge-declarations.fastapi]
    required = ["path", "status_code", "summary", "responses"]

    [edge-declarations.faststream]
    required = ["group_id", "parser", "decoder", "ack_policy"]
    ```
    """

    model_config = OPEN
    __pydantic_extra__: dict[str, Edge]  # type: ignore[assignment]

    @model_validator(mode="after")
    def _known(self) -> Self:
        """A block's name is a framework the library knows something about."""
        unknown = sorted(set(self.frameworks) - set(KNOWN))
        if unknown:
            listed = ", ".join(repr(name) for name in unknown)
            known = ", ".join(sorted(KNOWN))
            message = f"{listed}: the rule does not know this framework; it knows {known}"
            raise ValueError(message)
        return self

    @property
    def frameworks(self) -> dict[str, Edge]:
        return self.__pydantic_extra__


class EdgeDeclarations:
    """Fails when an entrance into the process did not say how it behaves.

    An entrance's decorator is a contract. For a route it is read by whoever
    reads the generated schema — a neighbouring service, a person writing a
    client — and a field that is not in the decorator does not exist for them,
    whatever the function body returns. For a subscription it is read by
    whoever is working out why a record was handled twice or not at all.

    The framework has the mechanism but demands none of it, and each default
    there is a decision made by somebody other than this project. A route with
    no `summary` lands in the schema with the function's name in place of a
    description, and with an empty `responses` it lands with a promise that it
    never refuses. A subscription with no `ack_policy` hands the broker back
    the record it has just delivered, and with no `auto_offset_reset` it skips
    the backlog a new group exists to read.

    The library knows what an entrance is in FastAPI and in FastStream: the
    method names, whether it is a decorator or a call, how the first argument
    is written. The project names one thing: what an entrance must declare.

    The body is declared apart from the rest and is not required where there
    is none: 204, 205 and 304 are statuses without a body, and a response
    model next to them promises what the protocol forbids. A status written as
    neither a number nor an `HTTPStatus` member reads as unknown, and an
    unknown one is taken to have a body: a check that fired needlessly is
    lifted by a mark, while one that stayed silent is a contract nobody will
    miss.

    An entrance taken out of the schema (`include_in_schema=False`) the rule
    leaves alone: the schema is what it protects, and such a route is not in it.

    Settings: one block per framework, with `required` in it.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = Edges
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(
        cls,
        *,
        file: ParsedFile,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        frameworks = settings_as(
            settings=settings,
            model=Edges,
            code=CODE,
        ).frameworks
        decorators = cls._decorators(tree=file.tree)
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.Call):
                continue
            found = cls._matched(
                call=node,
                frameworks=frameworks,
            )
            if found is None:
                continue
            shape, edge = found
            if shape.decorated and node not in decorators:
                continue
            yield from cls._judged(
                call=node,
                file=file,
                shape=shape,
                edge=edge,
            )

    @staticmethod
    def _decorators(*, tree: ast.Module) -> set[ast.Call]:
        """Calls that stand as a decorator: for such an entrance anything else is not it."""
        return {
            decorator
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            for decorator in node.decorator_list
            if isinstance(decorator, ast.Call)
        }

    @staticmethod
    def _matched(
        *,
        call: ast.Call,
        frameworks: dict[str, Edge],
    ) -> tuple[Shape, Edge] | None:
        """Which framework's entrance is declared here; `None` — not an entrance."""
        if not isinstance(call.func, ast.Attribute):
            return None
        for name, edge in frameworks.items():
            shape = KNOWN[name]
            if call.func.attr in shape.methods:
                return shape, edge
        return None

    @classmethod
    def _judged(
        cls,
        *,
        call: ast.Call,
        file: ParsedFile,
        shape: Shape,
        edge: Edge,
    ) -> Iterator[Violation]:
        if cls._unpublished(
            call=call,
            exempt=shape.exempt,
        ):
            return
        named = cls._name(
            call=call,
            shape=shape,
        )
        declared = {keyword.arg for keyword in call.keywords}
        yield from cls._first(
            call=call,
            file=file,
            shape=shape,
            named=named,
        )
        for wanted in edge.required:
            # One written positionally where it should not be was named above
            # already; a second remark about the same entrance reads as a second miss.
            if wanted in declared or (wanted == shape.named and call.args):
                continue
            yield cls._violation(
                call=call,
                file=file,
                message=f"{named} does not declare {wanted}=",
            )
        yield from cls._bodied(
            call=call,
            file=file,
            shape=shape,
            declared=declared,
            named=named,
        )

    @classmethod
    def _first(
        cls,
        *,
        call: ast.Call,
        file: ParsedFile,
        shape: Shape,
        named: str,
    ) -> Iterator[Violation]:
        """The first argument: written the wrong way, or not written at all."""
        if shape.named is not None:
            if call.args:
                yield cls._violation(
                    call=call,
                    file=file,
                    message=f"{named} gives the {shape.subject} positionally; write {shape.named}=",
                )
            return
        if not call.args:
            yield cls._violation(
                call=call,
                file=file,
                message=f"{named} does not name the {shape.subject}; it goes first, without a name",
            )

    @classmethod
    def _bodied(
        cls,
        *,
        call: ast.Call,
        file: ParsedFile,
        shape: Shape,
        declared: set[str | None],
        named: str,
    ) -> Iterator[Violation]:
        if shape.body is None or shape.body in declared:
            return
        if cls._status(call=call) in shape.bodiless:
            return
        yield cls._violation(
            call=call,
            file=file,
            message=(
                f"{named} does not declare {shape.body}= and answers with a body; "
                f"only {', '.join(str(status) for status in shape.bodiless)} go without it"
            ),
        )

    @staticmethod
    def _violation(
        *,
        call: ast.Call,
        file: ParsedFile,
        message: str,
    ) -> Violation:
        return Violation.from_node(
            node=call,
            path=file.path,
            code=CODE,
            message=message,
        )

    @staticmethod
    def _unpublished(
        *,
        call: ast.Call,
        exempt: str | None,
    ) -> bool:
        """The entrance said it is not in the schema."""
        return exempt is not None and any(
            keyword.arg == exempt
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is False
            for keyword in call.keywords
        )

    @staticmethod
    def _name(
        *,
        call: ast.Call,
        shape: Shape,
    ) -> str:
        """`POST '/tickets'`, `SUBSCRIBER 'bets.placed'` — however it is written.

        The subject of the declaration is read both from the position and from
        the keyword: a message has to name the entrance even in a file where
        the keyword is missing — "GET does not declare summary" in a module
        with six GETs names nothing.
        """
        attribute = call.func
        method = attribute.attr.upper() if isinstance(attribute, ast.Attribute) else ""
        written = [keyword.value for keyword in call.keywords if keyword.arg == shape.named]
        subject = call.args[:1] + written
        return f"{method} {ast.unparse(subject[0])}" if subject else method

    @staticmethod
    def _status(*, call: ast.Call) -> int | None:
        """The status, if it is written so that the file shows it."""
        for keyword in call.keywords:
            if keyword.arg != STATUS:
                continue
            match keyword.value:
                case ast.Constant(value=int() as status):
                    return status
                case ast.Attribute(value=ast.Name(id="HTTPStatus"), attr=name):
                    found = getattr(HTTPStatus, name, None)
                    return None if found is None else int(found)
                case _:
                    return None
        return None
