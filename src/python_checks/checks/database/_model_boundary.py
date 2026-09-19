"""ORM-модель не выходит за пределы слоя, который её понимает."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from python_checks.checks._location import place
from python_checks.checks.database._marker import MARKER
from python_checks.config import CheckSettings
from python_checks.core import Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from python_checks.checks._location import Place
    from python_checks.core import ParsedFile

CODE: Final = "model-boundary"

PRIVATE: Final = "_"
DOT: Final = "."
SEPARATOR: Final = "/"


class ModelBoundarySettings(CheckSettings):
    base: str = "Base"
    declared: tuple[str, ...] = ()
    built: tuple[str, ...] = ()


class ModelBoundary:
    """Падает, если ORM-модель объявлена, собрана или отдана не там.

    Модель — это описание таблицы, и три правила держат её описанием.

    Объявляется она там, где объявляются модели: где-то ещё это таблица,
    которую никто не ждёт по этому адресу, а autogenerate alembic видит только
    те модели, до которых дотянулись импорты их пакета.

    Собирается она только в репозиториях: собрать модель — значит записать
    строку, и модель, собранная в другом месте, либо не делает ничего — никто
    снаружи не держит сессию, чтобы её добавить, — либо это строка, записанная
    слоем, у которого нет транзакции, чтобы её записать.

    Публичный метод репозитория её не возвращает. Модель уносит с собой
    сессию: обращение к атрибуту после закрытия транзакции либо падает, либо
    лезет в базу из слоя, которому туда нельзя, а через связи оттуда достижима
    половина схемы, и запрос уходит из кода, который ни о каком соединении не
    просил. Репозитории возвращают DTO, идентификаторы, количества — всё, с чем
    слой базы уже закончил.

    Модель узнаётся двумя способами, и оба видны в одном файле: объявление —
    по базе `Base`, использование — по импорту из пакета моделей. Имя ни при
    чём: `SettingsModel` в настройках и `DeviceModel` в домене — не таблицы.

    Настройки: `base`, `declared`, `built`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = ModelBoundarySettings
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
            model=ModelBoundarySettings,
            code=CODE,
        )
        where = place(file=file)
        if where is None or not limits.declared:
            return
        models = cls._models(
            file=file,
            limits=limits,
        )
        found = [
            *cls._declared(
                file=file,
                where=where,
                limits=limits,
            ),
            *cls._built(
                file=file,
                where=where,
                limits=limits,
                models=models,
            ),
            *cls._returned(
                file=file,
                where=where,
                limits=limits,
                models=models,
            ),
        ]
        yield from sorted(found, key=lambda violation: (violation.line, violation.column))

    @classmethod
    def _declared(
        cls,
        *,
        file: ParsedFile,
        where: Place,
        limits: ModelBoundarySettings,
    ) -> Iterator[Violation]:
        """Модель, объявленная не в доме моделей."""
        if cls._inside(
            where=where,
            zones=limits.declared,
        ):
            return
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if any(cls._name(node=base) == limits.base for base in node.bases):
                yield Violation.from_node(
                    node=node,
                    path=file.path,
                    code=CODE,
                    message=(
                        f"{node.name} объявлена вне {', '.join(limits.declared)}; "
                        f"autogenerate видит только модели их пакета"
                    ),
                    end_line=node.body[0].lineno,
                )

    @classmethod
    def _built(
        cls,
        *,
        file: ParsedFile,
        where: Place,
        limits: ModelBoundarySettings,
        models: frozenset[str],
    ) -> Iterator[Violation]:
        """Модель, собранная там, где нечем записать строку."""
        if cls._inside(
            where=where,
            zones=limits.built + limits.declared,
        ):
            return
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.Call):
                continue
            built = cls._name(node=node.func)
            if built in models:
                yield Violation.from_node(
                    node=node,
                    path=file.path,
                    code=CODE,
                    message=(
                        f"{built}(...) собирается вне {', '.join(limits.built)}; "
                        f"собрать модель — значит записать строку"
                    ),
                )

    @classmethod
    def _returned(
        cls,
        *,
        file: ParsedFile,
        where: Place,
        limits: ModelBoundarySettings,
        models: frozenset[str],
    ) -> Iterator[Violation]:
        """Модель, отданная наружу публичным методом репозитория."""
        if not cls._inside(
            where=where,
            zones=limits.built,
        ):
            return
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if node.name.startswith(PRIVATE) or node.returns is None:
                continue
            returned = cls._named(
                node=node.returns,
                models=models,
            )
            if returned is None:
                continue
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                message=(
                    f"{node.name} возвращает {returned}; модель уносит с собой сессию — "
                    f"отдавай DTO, идентификатор, количество"
                ),
                end_line=node.body[0].lineno,
            )

    @classmethod
    def _models(
        cls,
        *,
        file: ParsedFile,
        limits: ModelBoundarySettings,
    ) -> frozenset[str]:
        """Имена, пришедшие импортом из пакета моделей."""
        names: set[str] = set()
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.ImportFrom) or node.module is None:
                continue
            if cls._home(
                module=node.module,
                zones=limits.declared,
            ):
                names.update(alias.asname or alias.name for alias in node.names)
        return frozenset(names)

    @staticmethod
    def _home(
        *,
        module: str,
        zones: tuple[str, ...],
    ) -> bool:
        path = SEPARATOR.join(module.split(DOT))
        return any(
            f"{SEPARATOR}{zone}{SEPARATOR}" in f"{SEPARATOR}{path}{SEPARATOR}" for zone in zones
        )

    @staticmethod
    def _inside(
        *,
        where: Place,
        zones: tuple[str, ...],
    ) -> bool:
        return any(where.holds(path=zone) for zone in zones)

    @classmethod
    def _named(
        cls,
        *,
        node: ast.expr,
        models: frozenset[str],
    ) -> str | None:
        """Имя модели, названное где-нибудь внутри аннотации."""
        for child in ast.walk(node):
            if isinstance(child, ast.expr) and cls._name(node=child) in models:
                return cls._name(node=child)
        return None

    @staticmethod
    def _name(*, node: ast.expr) -> str:
        match node:
            case ast.Name(id=name) | ast.Attribute(attr=name) | ast.Constant(value=str() as name):
                return name
            case _:
                return ""
