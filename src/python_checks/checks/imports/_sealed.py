"""Внутри запечатанной зоны чужих пакетов нет."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Final

from python_checks.checks.imports._base import ALLOW, ZONES
from python_checks.checks.imports._location import place
from python_checks.checks.imports._marker import MARKER
from python_checks.checks.imports._statements import imports
from python_checks.config import CheckSettings
from python_checks.core import Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from python_checks.checks.imports._location import Place
    from python_checks.core import ParsedFile

CODE: Final = "sealed-imports"


class SealedSettings(CheckSettings):
    zones: tuple[str, ...] = ZONES
    allow: dict[str, tuple[str, ...]] = dict(ALLOW)


class SealedImports:
    """Падает, если запечатанная зона импортирует чужой пакет.

    Правила и интерфейсы вокруг них не знают ничего, кроме стандартной
    библиотеки и кода самого сервиса: DTO здесь — dataclass, а не модель
    фреймворка. Список разрешённого белый, а не чёрный, потому что каждый новый
    фреймворк иначе попадает внутрь молча.

    Разрешения задаются по слою, а не на всю зону: `application` руководит и
    потому имеет право сказать, что произошло, а `domain` держит правила,
    верные независимо от того, слушает ли их кто-нибудь.

    Настройки: `zones`, `allow`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = SealedSettings
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(cls, *, file: ParsedFile, settings: CheckSettings) -> Iterator[Violation]:
        own = settings_as(settings=settings, model=SealedSettings, code=CODE)
        where = place(file=file)
        if where is None or not cls._sealed(where=where, zones=own.zones):
            return
        allowed = cls._allowed(where=where, allow=own.allow)
        for imported in imports(tree=file.tree):
            if imported.stdlib or imported.top in {where.package, *allowed}:
                continue
            yield Violation.from_node(
                node=imported.node,
                path=file.path,
                code=CODE,
                message=(
                    f"{imported.top} в {where.where}: запечатанная зона знает "
                    "только стандартную библиотеку и код сервиса"
                ),
            )

    @staticmethod
    def _sealed(*, where: Place, zones: tuple[str, ...]) -> bool:
        return any(part in zones for part in where.parts)

    @staticmethod
    def _allowed(*, where: Place, allow: dict[str, tuple[str, ...]]) -> frozenset[str]:
        """Что можно этому слою: зона у файла одна, а слой внутри неё — свой."""
        return frozenset(package for part in where.parts for package in allow.get(part, ()))
