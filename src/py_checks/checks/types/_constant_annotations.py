"""A name written as a constant promises it will not change, and says so by its type."""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks._kind import ENUMS
from py_checks.checks.types._marker import MARKER
from py_checks.config import CheckSettings
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.core import ParsedFile

CODE: Final = "constant-annotations"

FINAL: Final = "Final"
CLASS_VAR: Final = "ClassVar"

# The name is the promise itself: a lower-case binding at module level declares
# a variable and says so plainly, and it is not the rule's business.
NAME: Final = re.compile(r"^[A-Z][A-Z0-9_]*$")


class ConstantAnnotationsSettings(CheckSettings):
    module: str = FINAL
    inside_class: str = CLASS_VAR


class ConstantAnnotations:
    """Fails when a constant did not say by its type that it is one.

    An `UPPER_SNAKE` name is a promise; `Final` is what makes the promise
    checkable: without it the name reads as a constant and behaves as a
    variable, and anyone who imported the module is free to rebind it.

    Inside a class body the word is a different one, for a reason. `Final`
    there means the attribute cannot be overridden at all (PEP 591), and
    bounded primitives are built on exactly that overriding:
    `PositiveDecimal.BOUND` replaces the `BOUND` declared by the base.
    `ClassVar` says "belongs to the class, not the instance" and leaves
    overriding open — which is true of both.

    Enums are left alone: a member is a vocabulary, not a constant beside it.

    Settings: `module`, `inside-class` — the words it is said with.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = ConstantAnnotationsSettings
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
            model=ConstantAnnotationsSettings,
            code=CODE,
        )
        yield from cls._constants(
            file=file,
            body=file.tree.body,
            wanted=limits.module,
        )
        for node in ast.walk(file.tree):
            if isinstance(node, ast.ClassDef) and not cls._enum(node=node):
                yield from cls._constants(
                    file=file,
                    body=node.body,
                    wanted=limits.inside_class,
                )

    @classmethod
    def _constants(
        cls,
        *,
        file: ParsedFile,
        body: list[ast.stmt],
        wanted: str,
    ) -> Iterator[Violation]:
        for statement in body:
            name = cls._constant(node=statement)
            if name is None:
                continue
            yield Violation.from_node(
                node=statement,
                path=file.path,
                code=CODE,
                message=f"{name} is named as a constant but not declared with {wanted}",
            )

    @classmethod
    def _constant(cls, *, node: ast.stmt) -> str | None:
        """The name of a constant that lacks the word; otherwise `None`."""
        match node:
            case ast.Assign(targets=[ast.Name(id=name)]) if NAME.match(name):
                return name
            case ast.AnnAssign(target=ast.Name(id=name), annotation=annotation) if NAME.match(name):
                return None if cls._says(node=annotation) else name
            case _:
                return None

    @staticmethod
    def _says(*, node: ast.expr) -> bool:
        """Whether the annotation says that very word — bare or with a parameter."""
        outer = node.value if isinstance(node, ast.Subscript) else node
        match outer:
            case ast.Name(id=name) | ast.Attribute(attr=name):
                return name in (FINAL, CLASS_VAR)
            case _:
                return False

    @staticmethod
    def _enum(*, node: ast.ClassDef) -> bool:
        bases = {
            base.attr if isinstance(base, ast.Attribute) else getattr(base, "id", "")
            for base in node.bases
        }
        return bool(bases & ENUMS)
