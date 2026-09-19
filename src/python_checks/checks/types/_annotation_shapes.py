"""Форма, которая описывает значение беднее, чем оно есть."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from python_checks.checks.types._marker import MARKER
from python_checks.config import CheckSettings
from python_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from python_checks.core import ParsedFile

CODE: Final = "annotation-shapes"

MAPPING: Final = "dict"
TUPLE: Final = "tuple"


class AnnotationShapesSettings(CheckSettings):
    keys: tuple[str, ...] = ("str",)
    tuples: bool = True


class AnnotationShapes:
    """Падает, если форма названа так, что поля в ней безымянные.

    Словарь со строковым ключом читается как набор именованных полей, а
    `TypedDict` или dataclass говорят, каких именно. Ключи бывают и настоящими
    данными — мешок заголовков, носитель контекста трассировки, — и тогда
    строка помечается: `# type-ok: annotation-shapes: своя форма у propagator`.

    Кортеж фиксированной длины — тот, у которого последний аргумент не `...`, —
    называет поля позициями: `row[2]` не говорит ничего и молча переживает
    перестановку. Имена дают dataclass или `NamedTuple`, если это обязано
    остаться кортежем.

    Судится каждое место, где форма написана, а не только аннотации: словарь,
    собранный внутри функции, — та же неописанная форма одним вызовом позже, и
    обычно именно оттуда аннотация и взялась.

    Настройки: `keys` — какие ключи читаются как имена полей, `tuples` —
    судить ли кортежи фиксированной длины.
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
            written = cls._name(node=node.value)
            arguments = cls._arguments(node=node)
            if written == MAPPING and cls._keyed(
                arguments=arguments,
                keys=limits.keys,
            ):
                yield cls._says(
                    file=file,
                    node=node,
                    message=(
                        f"{ast.unparse(node)} читается как набор именованных полей; "
                        f"какие именно — скажет TypedDict или dataclass"
                    ),
                )
            if written == TUPLE and limits.tuples and cls._fixed(arguments=arguments):
                yield cls._says(
                    file=file,
                    node=node,
                    message=(
                        f"{ast.unparse(node)} называет поля позициями; имена даст dataclass, "
                        f"а NamedTuple — если это обязано остаться кортежем"
                    ),
                )

    @classmethod
    def _keyed(
        cls,
        *,
        arguments: list[ast.expr],
        keys: tuple[str, ...],
    ) -> bool:
        return bool(arguments) and cls._name(node=arguments[0]) in keys

    @staticmethod
    def _fixed(*, arguments: list[ast.expr]) -> bool:
        """Кортеж, у которого длина написана: последний аргумент не `...`."""
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

    @staticmethod
    def _name(*, node: ast.expr) -> str:
        match node:
            case ast.Name(id=name) | ast.Attribute(attr=name):
                return name
            case _:
                return ""
