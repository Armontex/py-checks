"""Из чего собрана колонка модели."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from python_checks.checks._location import place
from python_checks.checks._names import name
from python_checks.checks.database._marker import MARKER
from python_checks.config import CheckSettings
from python_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from python_checks.core import ParsedFile

CODE: Final = "model-columns"

MAPPED: Final = "Mapped"
AWARE: Final = "timezone"
NULLABLE: Final = "nullable"


class ModelColumnsSettings(CheckSettings):
    zones: tuple[str, ...] = ()
    factories: tuple[str, ...] = ("mapped_column", "Column")
    types: dict[str, str] = {}
    homes: dict[str, str] = {}
    defaults: tuple[str, ...] = ()
    unruled: tuple[str, ...] = ()
    aware: tuple[str, ...] = ()
    nullable: bool = True


class ModelColumns:
    """Падает, если колонка собрана не из того материала.

    Пять правил на одну таблицу настроек.

    `types` — материал, которому в колонке не место, и что писать вместо.
    Голый `Enum` — нативный тип Postgres: каждый новый член требует `ALTER
    TYPE`, а словари здесь чужие и расти будут. `Float` не держит цену точно, а
    колонка — это состояние, и ошибка округления копится с каждой записью.
    Голый `JSONB` — форма, которую никто не объявил: что положил писатель, то и
    получит каждый читатель, а разбор, поймавший бы пропущенный ключ, случается
    в каждом отдельно или нигде.

    `homes` — модуль, которому этот материал называть можно: там живёт обёртка
    над ним, и правило его не касается.

    `defaults` — все способы, которыми колонка заполняет себя сама. Значение по
    умолчанию — это значение, которого никто не писал: писатель пропустил
    колонку, строка всё равно получила число, и пропуск, который на пропущенном
    аргументе конструктора поймал бы проверяльщик типов, превращается в
    правдоподобную строку.

    `unruled` — встроенные типы в `Mapped[...]`. Такая колонка говорит, какой
    у значения вид, и ничего — какие значения допустимы, так что правило
    приходится помнить каждому писателю.

    `aware` — типы времени, которым нужен `timezone=True`: без него колонка
    хранит наивную метку, те самые настенные часы писателя, без подписи.

    `nullable` — аннотация и ключевое слово обязаны совпадать. SQLAlchemy
    разрешает им разойтись, и тогда аннотация лжёт: pyright рассуждает по ней,
    база держит ключевое слово, и одно из двух неверно на каждой строке.

    Настройки: `zones`, `factories`, `types`, `homes`, `defaults`, `unruled`,
    `aware`, `nullable`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = ModelColumnsSettings
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
            model=ModelColumnsSettings,
            code=CODE,
        )
        where = place(file=file)
        if where is None or not any(where.holds(path=zone) for zone in limits.zones):
            return
        for node in ast.walk(file.tree):
            if isinstance(node, ast.Call):
                yield from cls._material(
                    file=file,
                    node=node,
                    limits=limits,
                )
            if isinstance(node, ast.AnnAssign):
                yield from cls._annotation(
                    file=file,
                    node=node,
                    limits=limits,
                )

    @classmethod
    def _material(
        cls,
        *,
        file: ParsedFile,
        node: ast.Call,
        limits: ModelColumnsSettings,
    ) -> Iterator[Violation]:
        """Материал и то, чем колонка заполняет себя сама."""
        written = name(node=node.func)
        if written in limits.types and limits.homes.get(written) != file.path.stem:
            yield cls._says(
                file=file,
                node=node,
                message=limits.types[written],
            )
        if written in limits.aware and not cls._said(
            node=node,
            named=AWARE,
        ):
            yield cls._says(
                file=file,
                node=node,
                message=(
                    f"{written} без timezone=True хранит наивную метку времени; скажи timezone=True"
                ),
            )
        if written not in limits.factories:
            return
        for keyword in node.keywords:
            if keyword.arg in limits.defaults:
                yield cls._says(
                    file=file,
                    node=node,
                    message=(
                        f"{keyword.arg}= заполняет колонку за писателя, который её не написал; "
                        f"передай значение в запросе"
                    ),
                )

    @classmethod
    def _annotation(
        cls,
        *,
        file: ParsedFile,
        node: ast.AnnAssign,
        limits: ModelColumnsSettings,
    ) -> Iterator[Violation]:
        """Аннотация колонки: встроенный тип и согласие с `nullable=`."""
        inner = cls._mapped(node=node.annotation)
        if inner is None:
            return
        written, optional = inner
        if written in limits.unruled:
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                message=(f"{written} говорит вид, а не правило; возьми примитив с его границей"),
            )
        if not limits.nullable:
            return
        said = cls._nullable(
            node=node.value,
            limits=limits,
        )
        if said is not None and said != optional:
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                message=(
                    "аннотация и nullable= расходятся; во время работы побеждает то, "
                    "чего проверяльщик типов не видит"
                ),
            )

    @staticmethod
    def _nullable(
        *,
        node: ast.expr | None,
        limits: ModelColumnsSettings,
    ) -> bool | None:
        """Что сказано в `nullable=`, если вообще сказано."""
        if not isinstance(node, ast.Call) or name(node=node.func) not in limits.factories:
            return None
        for keyword in node.keywords:
            if keyword.arg == NULLABLE and isinstance(keyword.value, ast.Constant):
                return bool(keyword.value.value)
        return None

    @classmethod
    def _mapped(cls, *, node: ast.expr) -> tuple[str, bool] | None:
        """Имя внутри `Mapped[...]` и то, допускает ли оно `None`."""
        if not isinstance(node, ast.Subscript) or name(node=node.value) != MAPPED:
            return None
        match node.slice:
            case ast.Name(id=inside) | ast.Attribute(attr=inside):
                return inside, False
            case ast.BinOp(left=ast.Name(id=inside), op=ast.BitOr(), right=right):
                return inside, cls._none(node=right)
            case _:
                return None

    @staticmethod
    def _none(*, node: ast.expr) -> bool:
        return isinstance(node, ast.Constant) and node.value is None

    @staticmethod
    def _said(
        *,
        node: ast.Call,
        named: str,
    ) -> bool:
        return any(
            keyword.arg == named and keyword.value != ast.Constant(value=False)
            for keyword in node.keywords
        )

    @staticmethod
    def _says(
        *,
        file: ParsedFile,
        node: ast.Call,
        message: str,
    ) -> Violation:
        return Violation.from_node(
            node=node,
            path=file.path,
            code=CODE,
            message=message,
        )
