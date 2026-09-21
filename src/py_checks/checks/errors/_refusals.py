"""Отказ, на который вызывающему нечем ответить, — это не отказ, а падение."""

from __future__ import annotations

import ast
import builtins
from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks._location import ZonedSettings, zoned
from py_checks.checks._names import name
from py_checks.checks.errors._marker import MARKER
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.config import CheckSettings
    from py_checks.core import ParsedFile

CODE: Final = "refusals"

# Исключения, которые везёт сам интерпретатор, — по именам. Читаются из
# `builtins`, а не перечисляются: список пришлось бы кому-то поддерживать, а
# он меняется от версии к версии языка.
BUILTINS: Final[frozenset[str]] = frozenset(
    found
    for found, value in vars(builtins).items()
    if isinstance(value, type) and issubclass(value, BaseException)
)


class RefusalsSettings(ZonedSettings):
    """Где судим, чем несут код и что отказом не считается.

    `carries` не назван — у проекта нет своего кода отказа, и правило судит
    только встроенные исключения: у них кода нет ни в каком виде. Назван —
    своя ошибка обязана нести его с собой, кроме перечисленных в `internal`.
    """

    carries: str | None = None
    allow: tuple[str, ...] = ()
    internal: tuple[str, ...] = ()


class Refusals:
    """Падает, если отказ выходит наружу без кода, на который можно ветвиться.

    У отказа две половины. Фраза — человеку: её читают в логе, её переписывают,
    и зависеть от её слов нельзя ничему. Код — то, на что ветвится вызывающий:
    «денег не хватило» — это экран, «купон изменился» — это пересчёт. Поэтому
    фраза вольна меняться, а код нет, и держится это ровно до тех пор, пока
    каждое «нет», которое говорит модуль, несёт его с собой.

    Встроенное исключение кода не несёт вовсе. `ValueError`, пересёкший
    сценарий, — это отказ, о котором снаружи известно только то, что он
    случился, и периметр честно превращает его в 500: больше ему сделать не из
    чего. Что из встроенных отказом не считается, говорит `allow`:
    `NotImplementedError` — это не «нет», а метод, которого ещё нет, и
    единственное исключение, которое читатель не спутает с ответом.

    Своя ошибка кодом обязана, если она про игрока. Та, что говорит «код
    написан неверно» или «порт нарушил обещание», — внутренняя, ветвиться на
    неё некому, и её имена перечисляет `internal`.

    Настройки: `zones`, `carries`, `allow`, `internal`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = RefusalsSettings
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
            model=RefusalsSettings,
            code=CODE,
        )
        where = zoned(
            file=file,
            zones=limits.zones,
        )
        if where is None:
            return
        # По строкам, а не по обходу: `ast.walk` идёт в ширину, и отказ из
        # глубины `if` оказывается в выводе позже соседа, написанного ниже.
        yield from sorted(
            cls._found(
                file=file,
                limits=limits,
            ),
            key=lambda violation: (violation.line, violation.column),
        )

    @classmethod
    def _found(
        cls,
        *,
        file: ParsedFile,
        limits: RefusalsSettings,
    ) -> Iterator[Violation]:
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.Raise) or node.exc is None:
                continue
            raised = cls._raised(thrown=node.exc)
            if not raised:
                continue
            found = cls._said(
                raised=raised,
                thrown=node.exc,
                limits=limits,
            )
            if found is None:
                continue
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                message=found,
            )

    @staticmethod
    def _raised(*, thrown: ast.expr) -> str:
        """Что брошено: `raise Denied(...)` и `raise Denied` — одно и то же имя."""
        return name(node=thrown.func) if isinstance(thrown, ast.Call) else name(node=thrown)

    @classmethod
    def _said(
        cls,
        *,
        raised: str,
        thrown: ast.expr,
        limits: RefusalsSettings,
    ) -> str | None:
        """Чем плох этот `raise`; `None` — ничем."""
        if raised in BUILTINS:
            if raised in limits.allow:
                return None
            said = f" с {limits.carries}=" if limits.carries else ""
            return (
                f"бросает {raised}, а кода на нём нет: снаружи об этом отказе известно "
                f"только то, что он случился. Ответь своей ошибкой{said}"
            )
        if limits.carries is None or raised in limits.internal:
            return None
        if not isinstance(thrown, ast.Call):
            return f"бросает {raised} классом, без {limits.carries}="
        if any(keyword.arg == limits.carries for keyword in thrown.keywords):
            return None
        return (
            f"бросает {raised} без {limits.carries}=; код — то, на что ветвится "
            f"вызывающий, а фраза — человеку"
        )
