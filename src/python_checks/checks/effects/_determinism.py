"""Часы, случайность и новый идентификатор берутся портом, а не глобально."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from python_checks.checks._location import place
from python_checks.checks._names import matches
from python_checks.checks.effects._marker import MARKER
from python_checks.config import CheckSettings
from python_checks.core import Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from python_checks.core import ParsedFile

CODE: Final = "determinism"


class DeterminismSettings(CheckSettings):
    zones: tuple[str, ...] = ()
    sources: dict[str, str] = {}  # noqa: RUF012 — pydantic копирует значение по умолчанию


class Determinism:
    """Падает, если код сам читает часы, случайность или новый идентификатор.

    `datetime.now()`, `uuid4()` и `random.random()` делают сценарий
    непроверяемым: один и тот же вход даёт разный выход, и тест либо
    замораживает мир мокой, либо не утверждает ничего. Бизнес-код берёт их
    зависимостью — `self._clock.now()`, идентификатор, выданный на краю, — и
    вызов через порт правило не трогает: оно судит глобальные источники.

    Репозитории закрыты той же зоной, и там источник пишется на SQL:
    `func.gen_random_uuid()` внутри INSERT — то же решение этажом ниже, где его
    ещё хуже видно. В тесте о нём нечего утверждать, слой хранения становится
    автором идентификатора, о котором ему ничего не передавали, а среди uuid7
    появляется uuid4 — случайный там, где все остальные упорядочены, и
    упорядоченность — то, ради чего индекс по ним чего-то стоит.

    Имя сверяется с хвостом: `datetime.now` подходит и записи
    `datetime.datetime.now`, а `random.*` — любому вызову модуля целиком.

    Настройки: `zones`, `sources`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = DeterminismSettings
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
            model=DeterminismSettings,
            code=CODE,
        )
        where = place(file=file)
        if where is None or not limits.sources:
            return
        if not any(where.holds(path=zone) for zone in limits.zones):
            return
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.Call):
                continue
            called = ast.unparse(node.func)
            said = cls._source(
                called=called,
                sources=limits.sources,
            )
            if said is None:
                continue
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                message=f"{called}() не детерминирован; {said}",
            )

    @staticmethod
    def _source(
        *,
        called: str,
        sources: dict[str, str],
    ) -> str | None:
        """Причина, по которой такой вызов запрещён, если он в таблице."""
        return next(
            (
                said
                for pattern, said in sources.items()
                if matches(
                    called=called,
                    pattern=pattern,
                )
            ),
            None,
        )
