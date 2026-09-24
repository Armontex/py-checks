"""An operation is one class, one door and nothing beside it."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks._kind import Kind, declarations
from py_checks.checks._layout import SECTION, Layout, innermost
from py_checks.checks._location import place
from py_checks.checks.placement._marker import MARKER
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.checks._kind import Declaration
    from py_checks.checks._layout import Directory
    from py_checks.checks._location import Place
    from py_checks.config import CheckSettings
    from py_checks.core import ParsedFile

CODE: Final = "operation-shape"

PRIVATE: Final = "_"

STATIC: Final = "staticmethod"


@dataclass(frozen=True, slots=True)
class Shape:
    """The operation shape of this directory: the class name plus what the block says."""

    address: str
    suffix: str
    method: str | None
    forbids: tuple[str, ...]
    max_arguments: int | None


class OperationShape:
    """Fails when an operation is not shaped like an operation.

    The door's entrance is limited in arguments when a limit is set: whatever
    came from outside and is longer than a few fields is a command, a query or
    a DTO.

    Nothing stands beside the operation: no second class, no function, neither
    above nor below. A helper before the subject is a paragraph the reader
    skims; a helper after it is the same helper, shared with nobody: if the
    operation needs it, it becomes a private method; if two need it, it moves
    to where the shared code lives.

    Constants and aliases may stand there: a name is read where it is used.
    An enum may not, unlike in other directories: a vocabulary is a class, and
    an operation that needed one is naming something its module does not own.

    `__init__.py`, an empty module and a module with a leading underscore are
    left alone. So is a module that declared no operation at all: that is
    `required-class`'s to say, and a second opinion would report one mistake
    twice.

    Settings: `operation` in the shared `[layout]` table, beside `suffix`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = Layout
    section: ClassVar[str] = SECTION
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(
        cls,
        *,
        file: ParsedFile,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        layout = settings_as(
            settings=settings,
            model=Layout,
            code=CODE,
        ).directories
        where = place(file=file)
        if where is None or file.path.stem.startswith(PRIVATE):
            return
        rule = cls._rule(
            where=where,
            layout=layout,
        )
        if rule is None:
            return
        declared = list(declarations(tree=file.tree))
        subject = cls._subject(
            declared=declared,
            rule=rule,
        )
        found = list(
            cls._beside(
                file=file,
                declared=declared,
                subject=subject,
                rule=rule,
            )
        )
        if subject is not None and isinstance(subject.node, ast.ClassDef):
            found += [
                *cls._door(
                    file=file,
                    subject=subject,
                    node=subject.node,
                    rule=rule,
                ),
                *cls._input(
                    file=file,
                    subject=subject,
                    node=subject.node,
                    rule=rule,
                ),
                *cls._held(
                    file=file,
                    subject=subject,
                    node=subject.node,
                    rule=rule,
                ),
            ]
        yield from sorted(found, key=lambda violation: (violation.line, violation.column))

    @staticmethod
    def _rule(
        *,
        where: Place,
        layout: dict[str, Directory],
    ) -> Shape | None:
        """The shape of the innermost matching directory.

        A file may fall under several blocks: for `application/services`
        inside `application`, the one with the longer name and the closer
        place judges.
        """
        found = innermost(
            where=where,
            among=[
                (address, directory)
                for address, directory in layout.items()
                if directory.operation is not None and directory.suffix is not None
            ],
        )
        if found is None:
            return None
        address, directory = found
        # Both fields were checked by the filter above: a block without them never gets here.
        operation = directory.operation
        if operation is None or directory.suffix is None:
            return None
        return Shape(
            address=address,
            suffix=directory.suffix,
            method=operation.method,
            forbids=operation.forbids,
            max_arguments=operation.max_arguments,
        )

    @staticmethod
    def _subject(
        *,
        declared: list[Declaration],
        rule: Shape,
    ) -> Declaration | None:
        """The operation the module exists for, found by name, not by position.

        By position would be wrong: a class placed above the operation by
        mistake, the very thing the rule reports, would become the subject,
        and the module would hear that its vocabulary has no `execute()`. One
        mistake, one complaint.
        """
        classes = [one for one in declared if isinstance(one.node, ast.ClassDef)]
        named = [one for one in classes if one.name.endswith(rule.suffix)]
        return next(iter(named or classes), None)

    @classmethod
    def _beside(
        cls,
        *,
        file: ParsedFile,
        declared: list[Declaration],
        subject: Declaration | None,
        rule: Shape,
    ) -> Iterator[Violation]:
        """Everything that stands beside the operation: a second class or a function."""
        for one in declared:
            if one.kind is Kind.ALIAS or one is subject:
                continue
            if one.kind is Kind.FUNCTION:
                yield cls._says(
                    file=file,
                    declared=one,
                    message=(
                        f"{one.name}() stands beside the operation; a helper it needs is "
                        f"a private method, one that two need is shared code"
                    ),
                )
                continue
            yield cls._says(
                file=file,
                declared=one,
                message=(
                    f"{one.name} stands beside the operation; in {rule.address} a module "
                    f"declares one class and nothing else"
                ),
            )

    @classmethod
    def _door(
        cls,
        *,
        file: ParsedFile,
        subject: Declaration,
        node: ast.ClassDef,
        rule: Shape,
    ) -> Iterator[Violation]:
        """The operation's single public door."""
        if rule.method is None:
            return
        public = cls._public(node=node)
        names = [method.name for method in public]
        if names == [rule.method]:
            return
        if not public:
            yield cls._says(
                file=file,
                declared=subject,
                message=(
                    f"{subject.name} has no public method; an operation is asked "
                    f"through one, and it is called {rule.method}()"
                ),
            )
            return
        yield Violation.from_node(
            node=public[0],
            path=file.path,
            code=CODE,
            message=(
                f"{subject.name} offers {', '.join(f'{name}()' for name in names)}; "
                f"an operation has one public method, and it is {rule.method}(); "
                f"make the rest private or move them to another class"
            ),
        )

    @classmethod
    def _input(
        cls,
        *,
        file: ParsedFile,
        subject: Declaration,
        node: ast.ClassDef,
        rule: Shape,
    ) -> Iterator[Violation]:
        """How many arguments the entrance takes."""
        if rule.max_arguments is None:
            return
        for method in cls._public(node=node):
            count = cls._arguments(node=method)
            if count <= rule.max_arguments:
                continue
            yield Violation.from_node(
                node=method,
                path=file.path,
                code=CODE,
                message=(
                    f"{subject.name}.{method.name} takes {count} arguments, the limit is "
                    f"{rule.max_arguments}; pass a command, a query or a DTO"
                ),
                # The mark is accepted on any line of the signature.
                end_line=max(method.body[0].lineno - 1, method.lineno),
            )

    @classmethod
    def _arguments(cls, *, node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        """Everything the caller fills; the first argument of a method does not count.

        By position, not by name: `self` in a `@staticmethod` is an ordinary argument.
        """
        receiver = 0 if cls._static(node=node) else 1
        named = [*node.args.posonlyargs, *node.args.args][receiver:]
        collectors = [one for one in (node.args.vararg, node.args.kwarg) if one is not None]
        return len(named) + len(node.args.kwonlyargs) + len(collectors)

    @staticmethod
    def _static(*, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        names = {
            item.id if isinstance(item, ast.Name) else getattr(item, "attr", "")
            for item in node.decorator_list
        }
        return STATIC in names

    @classmethod
    def _held(
        cls,
        *,
        file: ParsedFile,
        subject: Declaration,
        node: ast.ClassDef,
        rule: Shape,
    ) -> Iterator[Violation]:
        """A type the operation does not hold, in a field or in a parameter."""
        for annotation in cls._annotations(node=node):
            held = next(
                (
                    name
                    for name in cls._typed(node=annotation)
                    for mark in rule.forbids
                    if mark in name
                ),
                None,
            )
            if held is None:
                continue
            yield Violation.from_node(
                node=annotation,
                path=file.path,
                code=CODE,
                message=(
                    f"{subject.name} holds {held}; an operation is handed what it writes "
                    f"through, and the transaction stays with the caller"
                ),
            )

    @staticmethod
    def _public(*, node: ast.ClassDef) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
        """The methods a caller can reach, in order of declaration.

        A `@property` counts: it is something read off the operation, and an
        operation has nothing to offer but the one door.
        """
        return [
            statement
            for statement in node.body
            if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef)
            and not statement.name.startswith(PRIVATE)
        ]

    @staticmethod
    def _annotations(*, node: ast.ClassDef) -> Iterator[ast.expr]:
        """Everything the class declared with an annotation: fields and method parameters."""
        for child in ast.walk(node):
            match child:
                case ast.AnnAssign(annotation=annotation):
                    yield annotation
                case ast.arg(annotation=ast.expr() as annotation):
                    yield annotation
                case _:
                    continue

    @staticmethod
    def _typed(*, node: ast.expr) -> Iterator[str]:
        """The type names written inside an annotation."""
        for child in ast.walk(node):
            match child:
                case ast.Name(id=name) | ast.Attribute(attr=name):
                    yield name
                # A forward reference `uow: "PlacementUnitOfWork"` is the same
                # dependency, written for the type checker.
                case ast.Constant(value=str() as text):
                    yield text
                case _:
                    continue

    @staticmethod
    def _says(
        *,
        file: ParsedFile,
        declared: Declaration,
        message: str,
    ) -> Violation:
        return Violation.from_node(
            node=declared.node,
            path=file.path,
            code=CODE,
            message=message,
        )
