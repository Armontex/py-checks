"""A shape that describes a value more poorly than the value is."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks._names import name
from py_checks.checks.types._marker import MARKER
from py_checks.config import CheckSettings
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.core import ParsedFile

CODE: Final = "annotation-shapes"

MAPPING: Final = "dict"
TUPLE: Final = "tuple"


class AnnotationShapesSettings(CheckSettings):
    keys: tuple[str, ...] = ("str",)
    tuples: bool = True


class AnnotationShapes:
    """Fails when a shape is named such that its fields have no names.

    A dict with a string key reads as a set of named fields, and a `TypedDict`
    or a dataclass says which ones. Sometimes the keys are genuine data — a bag
    of headers, a trace-context carrier — and then the line is marked:
    `# type-ok: annotation-shapes: the propagator's own shape`.

    A fixed-length tuple — one whose last argument is not `...` — names its
    fields by position: `row[2]` says nothing and survives a reordering in
    silence. Names come from a dataclass, or from a `NamedTuple` if it has to
    stay a tuple.

    Every place the shape is written is judged, not only annotations: a dict
    built inside a function is the same undescribed shape one call later, and
    that is usually where the annotation came from in the first place.

    Settings: `keys` — which keys read as field names, `tuples` — whether to
    judge fixed-length tuples.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = AnnotationShapesSettings
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
            model=AnnotationShapesSettings,
            code=CODE,
        )
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.Subscript):
                continue
            written = name(node=node.value)
            arguments = cls._arguments(node=node)
            if written == MAPPING and cls._keyed(
                arguments=arguments,
                keys=limits.keys,
            ):
                yield cls._says(
                    file=file,
                    node=node,
                    message=(
                        f"{ast.unparse(node)} reads as a set of named fields; "
                        f"a TypedDict or a dataclass will say which ones"
                    ),
                )
            if written == TUPLE and limits.tuples and cls._fixed(arguments=arguments):
                yield cls._says(
                    file=file,
                    node=node,
                    message=(
                        f"{ast.unparse(node)} names its fields by position; a dataclass gives "
                        f"them names, or a NamedTuple if it has to stay a tuple"
                    ),
                )

    @staticmethod
    def _keyed(
        *,
        arguments: list[ast.expr],
        keys: tuple[str, ...],
    ) -> bool:
        return bool(arguments) and name(node=arguments[0]) in keys

    @staticmethod
    def _fixed(*, arguments: list[ast.expr]) -> bool:
        """A tuple whose length is written out: the last argument is not `...`."""
        if not arguments:
            return False
        last = arguments[-1]
        return not (isinstance(last, ast.Constant) and last.value is Ellipsis)

    @staticmethod
    def _arguments(*, node: ast.Subscript) -> list[ast.expr]:
        inside = node.slice
        return list(inside.elts) if isinstance(inside, ast.Tuple) else [inside]

    @staticmethod
    def _says(
        *,
        file: ParsedFile,
        node: ast.Subscript,
        message: str,
    ) -> Violation:
        return Violation.from_node(
            node=node,
            path=file.path,
            code=CODE,
            message=message,
        )
