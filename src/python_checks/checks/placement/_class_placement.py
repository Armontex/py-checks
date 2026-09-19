"""Класс лежит там, где лежат классы его вида."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Final, Self

from pydantic import model_validator

from python_checks.checks._kind import Kind, declarations
from python_checks.checks._location import place
from python_checks.checks.placement._marker import MARKER
from python_checks.config import CheckSettings
from python_checks.core import Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from python_checks.checks._kind import Declaration
    from python_checks.checks._location import Place
    from python_checks.core import ParsedFile

CODE: Final = "class-placement"


class Rule(CheckSettings):
    """Кому куда: вид объявления или суффикс имени — и где ему место.

    `area` сужает правило до части дерева. Без него `dataclass` пришлось бы
    держать в `dto/` по всему сервису, а доменный value object — тоже
    dataclass, и живёт он в домене.

    `inside` перечисляет равноправные адреса: `errors` и `exceptions` — это
    директория и модуль, и словарь отказов законно лежит в любом из них.
    """

    kind: Kind | None = None
    suffix: str | None = None
    inside: tuple[str, ...]
    area: str | None = None

    @model_validator(mode="after")
    def _one_subject(self) -> Self:
        if (self.kind is None) == (self.suffix is None):
            message = "правилу нужен ровно один признак: `kind` или `suffix`"
            raise ValueError(message)
        return self

    def about(self, *, declared: Declaration) -> bool:
        if self.suffix is not None:
            return declared.name.endswith(self.suffix)
        return declared.kind is self.kind

    @property
    def said(self) -> str:
        if self.suffix is not None:
            return f"кончается на {self.suffix}"
        return f"— {self.kind.said}" if self.kind is not None else ""


class ClassPlacementSettings(CheckSettings):
    rules: tuple[Rule, ...] = ()


class ClassPlacement:
    """Падает, если класс лежит не там, где лежат классы его вида.

    Директория называет вид, и читатель находит порт, не открывая файла.
    Правила проверяются по порядку, первое подошедшее отвечает за объявление:
    исключение — это исключение, даже если его имя кончается на `Service`.

    Область (`area`) — половина смысла: `dataclass` обязан лежать в `dto/`
    только внутри `application`, потому что доменный value object — тоже
    dataclass, и живёт он в домене.

    Настройка: `rules`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = ClassPlacementSettings
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(
        cls,
        *,
        file: ParsedFile,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        rules = settings_as(
            settings=settings,
            model=ClassPlacementSettings,
            code=CODE,
        ).rules
        where = place(file=file)
        if where is None:
            return
        for declared in declarations(tree=file.tree):
            rule = cls._rule(
                declared=declared,
                where=where,
                rules=rules,
            )
            if rule is None:
                continue
            yield Violation.from_node(
                node=declared.node,
                path=file.path,
                code=CODE,
                message=(f"{declared.name} {rule.said}; ему место в {', '.join(rule.inside)}"),
            )

    @classmethod
    def _rule(
        cls,
        *,
        declared: Declaration,
        where: Place,
        rules: tuple[Rule, ...],
    ) -> Rule | None:
        """Первое правило, которое про это объявление и которое нарушено."""
        for rule in rules:
            if not rule.about(declared=declared):
                continue
            if rule.area is not None and not where.holds(path=rule.area):
                continue
            if any(where.holds(path=address) for address in rule.inside):
                return None
            return rule
        return None
