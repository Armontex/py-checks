"""Поле настроек названо целиком: и как приходит, и какие значения допустимы."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from python_checks.checks._location import ZonedSettings, zoned
from python_checks.checks._names import walked
from python_checks.checks.types._marker import MARKER
from python_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from python_checks.config import CheckSettings
    from python_checks.core import ParsedFile

CODE: Final = "config-fields"

# Классы, которые держат словарь или интерфейс, а не поля настроек.
NOT_SETTINGS: Final[frozenset[str]] = frozenset(
    {"Enum", "StrEnum", "IntEnum", "IntFlag", "Flag", "Protocol", "TypedDict"},
)

# Аннотация, которая говорит, как значение хранится, и ничего — какие значения
# допустимы. Всё остальное — имя, а имя это место, где правило может жить.
BOUNDS: Final[dict[str, tuple[str, ...]]] = {
    "int": ("ge", "gt", "le", "lt"),
    "float": ("ge", "gt", "le", "lt"),
    # `max_length` тут отсутствует намеренно: потолок говорит, какой длины
    # значение может быть, а не что оно вообще есть, — а речь именно о пустой
    # строке, которой оборачивается неустановленная переменная.
    "str": ("min_length", "pattern"),
}

CLASS_VAR: Final = "ClassVar"

# Поле, собранное фабрикой, — это вложенная секция, а не значение: переменной у
# него нет, её читают поля внутри.
FACTORY: Final = "default_factory"


class ConfigFieldsSettings(ZonedSettings):
    factory: str = "Field"
    alias: str | None = None
    bounds: dict[str, tuple[str, ...]] = BOUNDS


class ConfigFields:
    """Падает, если поле настроек ничем не ограничено.

    Значение приходит текстом из окружения, которое никто не ревьюит, поэтому
    обе половины объявления обязательны.

    Поле объявляется через `Field(...)`: там живут псевдоним переменной,
    значение по умолчанию и ограничения, а голое `name: str = "x"` молча
    роняет все три.

    Поле с голым числом называет границу — `ge`, `gt`, `le`, `lt` — или
    аннотируется типом, который её несёт. Без этого `POSTGRES_POOL_SIZE=0` и
    пул на пятьсот принимаются здесь и падают где-то там, где в трейсбеке
    настроек уже не видно.

    Голая строка — та же дыра с более тихим отказом: неустановленная переменная
    приходит пустой строкой, и пустой адрес брокера, DSN или имя топика
    принимаются как настройка. Поле называет `min_length` или `pattern`, либо
    несёт тип, который это делает.

    Поле называет переменную, из которой читается (`alias`, у pydantic это
    `validation_alias`). Без неё имя переменной знает один pydantic — он
    выводит его из имени поля и приставки, — и ни `.env.example`, собранный из
    этих же классов, ни человек, ищущий, откуда берётся значение, назвать её не
    могут. Поле, собранное `default_factory`, — исключение: это вложенная
    секция, а не значение, и переменные читают её собственные поля.

    `ClassVar` — не поле настроек, а константа рядом с ними.

    Настройки: `zones`, `factory`, `alias`, `bounds`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = ConfigFieldsSettings
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
            model=ConfigFieldsSettings,
            code=CODE,
        )
        where = zoned(
            file=file,
            zones=limits.zones,
        )
        if where is None:
            return
        for node in ast.walk(file.tree):
            if isinstance(node, ast.ClassDef) and cls._settings(node=node):
                yield from cls._fields(
                    file=file,
                    node=node,
                    limits=limits,
                )

    @classmethod
    def _fields(
        cls,
        *,
        file: ParsedFile,
        node: ast.ClassDef,
        limits: ConfigFieldsSettings,
    ) -> Iterator[Violation]:
        for statement in node.body:
            if not isinstance(statement, ast.AnnAssign):
                continue
            if not isinstance(statement.target, ast.Name):
                continue
            named = frozenset(walked(node=statement.annotation))
            if CLASS_VAR in named:
                continue
            reason = cls._reason(
                statement=statement,
                named=named,
                limits=limits,
            )
            if reason is None:
                continue
            yield Violation.from_node(
                node=statement,
                path=file.path,
                code=CODE,
                message=f"{node.name}.{statement.target.id} {reason}",
            )

    @classmethod
    def _reason(
        cls,
        *,
        statement: ast.AnnAssign,
        named: frozenset[str],
        limits: ConfigFieldsSettings,
    ) -> str | None:
        """Чем поле не закрыто, или `None`, если закрыто."""
        if not cls._declared(
            node=statement.value,
            factory=limits.factory,
        ):
            if statement.value is None:
                return (
                    f"объявлено без значения; поле настроек объявляют через {limits.factory}(...)"
                )
            return f"объявлено не через {limits.factory}(...)"
        if (
            limits.alias is not None
            and not cls._states(
                node=statement.value,
                wanted=(FACTORY,),
            )
            and not cls._states(
                node=statement.value,
                wanted=(limits.alias,),
            )
        ):
            return (
                f"не называет {limits.alias}=; без него имя переменной знает "
                f"один pydantic, а `.env.example` собирается из этих же полей"
            )
        wanted = cls._wanted(
            named=named,
            bounds=limits.bounds,
        )
        if wanted and not cls._states(
            node=statement.value,
            wanted=wanted,
        ):
            return (
                f"ничем не ограничено; назови одно из {', '.join(wanted)} "
                f"или аннотируй типом, который несёт это правило"
            )
        return None

    @staticmethod
    def _wanted(
        *,
        named: frozenset[str],
        bounds: dict[str, tuple[str, ...]],
    ) -> tuple[str, ...]:
        """Какие ограничения задолжала аннотация.

        `str | None` — это строка, а `int | None` — число: объединение говорит
        о том, есть ли значение, а не о том, какие значения допустимы. Имя, не
        попавшее в таблицу, — уже правило: ограничение живёт в нём.
        """
        if not named or not named <= frozenset(bounds):
            return ()
        listed = [one for name in sorted(named) for one in bounds[name]]
        return tuple(dict.fromkeys(listed))

    @staticmethod
    def _declared(
        *,
        node: ast.expr | None,
        factory: str,
    ) -> bool:
        match node:
            case ast.Call(func=ast.Name(id=name) | ast.Attribute(attr=name)):
                return name == factory
            case _:
                return False

    @staticmethod
    def _states(
        *,
        node: ast.expr | None,
        wanted: tuple[str, ...],
    ) -> bool:
        if not isinstance(node, ast.Call):
            return False
        return any(keyword.arg in wanted for keyword in node.keywords)

    @staticmethod
    def _settings(*, node: ast.ClassDef) -> bool:
        """Класс полей настроек, а не словарь и не интерфейс рядом с ними."""
        bases = {
            base.attr if isinstance(base, ast.Attribute) else getattr(base, "id", "")
            for base in node.bases
        }
        return not bases & NOT_SETTINGS
