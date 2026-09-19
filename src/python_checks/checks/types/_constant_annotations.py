"""Имя, написанное как константа, обещает неизменность — и говорит это типом."""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING, ClassVar, Final

from python_checks.checks._kind import ENUMS
from python_checks.checks.types._marker import MARKER
from python_checks.config import CheckSettings
from python_checks.core import Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from python_checks.core import ParsedFile

CODE: Final = "constant-annotations"

FINAL: Final = "Final"
CLASS_VAR: Final = "ClassVar"

# Имя — это и есть обещание: строчная привязка на уровне модуля объявляет
# переменную и говорит об этом прямо, и правилу до неё дела нет.
NAME: Final = re.compile(r"^[A-Z][A-Z0-9_]*$")


class ConstantAnnotationsSettings(CheckSettings):
    module: str = FINAL
    inside_class: str = CLASS_VAR


class ConstantAnnotations:
    """Падает, если константа не сказала типом, что она константа.

    Имя `UPPER_SNAKE` — обещание, `Final` — то, что делает обещание
    проверяемым: без него имя читается как константа, а ведёт себя как
    переменная, и любой импортировавший модуль волен её перепривязать.

    В теле класса слово другое, и по причине. `Final` там означает, что
    атрибут нельзя переопределить вообще (PEP 591), а ограниченные примитивы
    построены ровно на переопределении: `PositiveDecimal.BOUND` заменяет
    `BOUND`, объявленный базой. `ClassVar` говорит «принадлежит классу, а не
    экземпляру» и переопределение оставляет открытым — это верно про оба.

    Перечисления не трогаются: член — это словарь, а не константа рядом с ним.

    Настройки: `module`, `inside-class` — какими словами это говорится.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = ConstantAnnotationsSettings
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
                message=f"{name} названо константой, но не объявлено через {wanted}",
            )

    @classmethod
    def _constant(cls, *, node: ast.stmt) -> str | None:
        """Имя константы, которой не хватает слова; иначе `None`."""
        match node:
            case ast.Assign(targets=[ast.Name(id=name)]) if NAME.match(name):
                return name
            case ast.AnnAssign(target=ast.Name(id=name), annotation=annotation) if NAME.match(name):
                return None if cls._says(node=annotation) else name
            case _:
                return None

    @staticmethod
    def _says(*, node: ast.expr) -> bool:
        """Сказано ли в аннотации то самое слово — голым или с параметром."""
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
