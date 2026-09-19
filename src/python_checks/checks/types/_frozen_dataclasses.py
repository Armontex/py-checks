"""dataclass объявлен так, чтобы значение оставалось значением."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from python_checks.checks._location import place
from python_checks.checks.types._marker import MARKER
from python_checks.config import CheckSettings
from python_checks.core import Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from python_checks.core import ParsedFile

CODE: Final = "frozen-dataclasses"

DECORATOR: Final = "dataclass"


class FrozenDataclassesSettings(CheckSettings):
    zones: tuple[str, ...] = ()
    options: tuple[str, ...] = ("frozen", "slots", "kw_only")


class FrozenDataclasses:
    """Падает, если dataclass в зоне объявлен без нужных аргументов.

    Объект дела — это значение: собрали один раз и не меняли, поэтому
    существующий объект не может исподтишка съехать в недопустимое состояние.
    `frozen` это покупает, `slots` не даёт опечатке завести атрибут, которого
    никто не объявлял, а `kw_only` — перепутать местами два поля одного типа:
    у значения из четырёх строк порядок помнит только автор.

        @dataclass(frozen=True, slots=True, kw_only=True)
        class Price: ...

    Зона проектная: держать значения неизменяемыми имеет смысл там, где живут
    правила, а не в конфиге и не в проводке. Без зон правило молчит.

    Настройки: `zones`, `options`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = FrozenDataclassesSettings
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
            model=FrozenDataclassesSettings,
            code=CODE,
        )
        where = place(file=file)
        if where is None or not any(where.holds(path=zone) for zone in limits.zones):
            return
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.ClassDef):
                continue
            decorator = cls._decorator(node=node)
            if decorator is None:
                continue
            missing = tuple(
                option for option in limits.options if option not in cls._enabled(node=decorator)
            )
            if not missing:
                continue
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                message=(
                    f"dataclass {node.name} объявлен без "
                    f"{', '.join(f'{option}=True' for option in missing)}"
                ),
            )

    @classmethod
    def _decorator(cls, *, node: ast.ClassDef) -> ast.expr | None:
        """Декоратор `@dataclass`, с аргументами или без."""
        for item in node.decorator_list:
            called = item.func if isinstance(item, ast.Call) else item
            if cls._name(node=called) == DECORATOR:
                return item
        return None

    @classmethod
    def _enabled(cls, *, node: ast.expr) -> frozenset[str]:
        """Аргументы декоратора, выставленные в `True`."""
        if not isinstance(node, ast.Call):
            return frozenset()
        return frozenset(
            keyword.arg
            for keyword in node.keywords
            if keyword.arg is not None and cls._true(node=keyword.value)
        )

    @staticmethod
    def _true(*, node: ast.expr) -> bool:
        return isinstance(node, ast.Constant) and node.value is True

    @staticmethod
    def _name(*, node: ast.expr) -> str:
        match node:
            case ast.Name(id=name) | ast.Attribute(attr=name):
                return name
            case _:
                return ""
