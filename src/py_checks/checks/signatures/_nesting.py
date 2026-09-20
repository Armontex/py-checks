"""Глубина вложенности управляющих конструкций."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final, Self

from pydantic import model_validator

from py_checks.checks.signatures._marker import MARKER
from py_checks.config import OPEN, CheckSettings
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.core import ParsedFile

CODE: Final = "nesting"

# Виды, о которых правило умеет говорить. `with` в списке есть, но держать его
# в таблице проекту незачем: вложенный `with` ловит ruff `SIM117`, с автофиксом
# и с готовым ответом — «сделай один `with a, b:`».
KINDS: Final[dict[str, tuple[type[ast.stmt], ...]]] = {
    "try": (ast.Try, ast.TryStar),
    "with": (ast.With, ast.AsyncWith),
    "if": (ast.If,),
    "for": (ast.For, ast.AsyncFor),
    "while": (ast.While,),
    "match": (ast.Match,),
}

# Списки инструкций, которые узел держит в себе.
BRANCHES: Final[tuple[str, ...]] = ("body", "orelse", "finalbody")


class NestingSettings(CheckSettings):
    """Секция `[nesting]`: конструкция — и её предел вложенности."""

    model_config = OPEN

    __pydantic_extra__: dict[str, int]  # type: ignore[assignment]

    @property
    def limits(self) -> dict[str, int]:
        return self.__pydantic_extra__

    @model_validator(mode="after")
    def _known(self) -> Self:
        unknown = sorted(set(self.limits) - set(KINDS))
        if unknown:
            message = f"неизвестные конструкции: {', '.join(unknown)}"
            raise ValueError(message)
        if any(limit < 1 for limit in self.limits.values()):
            message = "предел вложенности — целое от единицы"
            raise ValueError(message)
        return self


class Nesting:
    """Падает, если управляющие конструкции вложены глубже предела.

    Глубина — это место, где логику перестают читать и начинают расшифровывать.
    Предел у каждого вида свой, потому что стоят они разного: второй `try`
    внутри первого прячет, какая строка бросила, а второй уровень `if` — это
    обычная развилка, и лишним становится третий.

    `elif` — ветка, а не уровень, и уровнем не считается. Написанный
    развёрнуто `else:` с `if` внутри — считается: это и есть лишний отступ.

    Вложенный `with` в таблицу лучше не класть: его ловит ruff `SIM117`, с
    автофиксом и с ответом на месте.

    Настройка: имя конструкции — предел: `try = 1`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = NestingSettings
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
            model=NestingSettings,
            code=CODE,
        ).limits
        if not limits:
            return
        depths = dict.fromkeys(limits, 0)
        for node in file.tree.body:
            yield from cls._visit(
                file=file,
                node=node,
                depths=depths,
                limits=limits,
            )

    @classmethod
    def _visit(
        cls,
        *,
        file: ParsedFile,
        node: ast.stmt,
        depths: dict[str, int],
        limits: dict[str, int],
    ) -> Iterator[Violation]:
        kind = cls._kind(
            node=node,
            limits=limits,
        )
        if kind is not None:
            depth = depths[kind] + 1
            if depth > limits[kind]:
                yield Violation.from_node(
                    node=node,
                    path=file.path,
                    code=CODE,
                    message=f"{kind} вложен на {depth}, предел {limits[kind]}",
                )
            depths = {**depths, kind: depth}
        for child in cls._children(node=node):
            inner = depths
            if isinstance(node, ast.If) and cls._elif(
                node=node,
                child=child,
            ):
                inner = {**depths, "if": depths["if"] - 1}
            yield from cls._visit(
                file=file,
                node=child,
                depths=inner,
                limits=limits,
            )

    @staticmethod
    def _kind(
        *,
        node: ast.stmt,
        limits: dict[str, int],
    ) -> str | None:
        return next((kind for kind in limits if isinstance(node, KINDS[kind])), None)

    @staticmethod
    def _children(*, node: ast.stmt) -> Iterator[ast.stmt]:
        for field in BRANCHES:
            yield from getattr(node, field, [])
        for handler in getattr(node, "handlers", []):
            yield from handler.body

    @staticmethod
    def _elif(
        *,
        node: ast.If,
        child: ast.stmt,
    ) -> bool:
        """`elif` стоит в той же колонке, что его `if`; написанный `else: if` — нет."""
        return isinstance(child, ast.If) and child.col_offset == node.col_offset
