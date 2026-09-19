"""У зависимости есть потолок, иначе версию выбирает решатель."""

from __future__ import annotations

import re
import tomllib
from typing import TYPE_CHECKING, Any, ClassVar, Final

from python_checks.checks.hygiene._marker import MARKER
from python_checks.config import CheckSettings
from python_checks.core import Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

CODE: Final = "dependency-bounds"

MANIFEST: Final = "pyproject.toml"
MARKERS: Final = ";"
FIRST: Final = 1

# Имя, за которым идут extras и спецификаторы. `packaging` разобрал бы это
# правильно и не является зависимостью хуков, а формы, которые встречаются в
# манифесте, узки настолько, что выражение говорит всё правило целиком.
REQUIREMENT: Final = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?(?P<rest>.*)$"
)


class DependencyBoundsSettings(CheckSettings):
    ceilings: tuple[str, ...] = ("==", "<=", "<", "~=", "===")
    pins: tuple[str, ...] = ("rev", "tag")


class DependencyBounds:
    """Падает, если зависимость может уехать на версию, которую никто не запускал.

    Требование объявляет потолок одним из двух способов: точной версией
    (`greenlet==3.5.5`) или парой «пол и потолок» (`pydantic>=2.13.5,<3`,
    `structlog~=26.1` — то же самое, сказанное иначе).

    Отвергается голый пол — `pre-commit>=4.6.2`. Читается он как минимум, а
    ведёт себя как «что новее на момент, когда кто-то пересобрал лок», то есть
    как другой сервис после каждого обновления: выходит мажор, лок двигается, и
    изменение приезжает в том коммите, который случайно тронул зависимости.
    Потолок делает этот приезд осознанной правкой, за которой стоит диff и
    прогон тестов, — единственное место, где ломающее обновление вообще можно
    прочитать.

    Лок этого не заменяет: `uv.lock` фиксирует то, что стоит сегодня, и он
    пересобирается — ограничение это то, что переживает пересборку.

    Проверяются все группы: зависимость тестов решает, проходит ли набор, а
    сборочная — существует ли колесо.

    Исключение одно, и оно несёт свой собственный гвоздь: требование без
    спецификаторов, чьё имя лежит в `[tool.uv.sources]` с `rev` или `tag`.
    Коммит — самый тесный потолок, какой бывает.

    Настройки: `ceilings`, `pins`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = DependencyBoundsSettings
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(
        cls,
        *,
        root: Path,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        limits = settings_as(
            settings=settings,
            model=DependencyBoundsSettings,
            code=CODE,
        )
        path = root / MANIFEST
        if not path.is_file():
            return
        text = path.read_text(encoding="utf-8")
        manifest = tomllib.loads(text)
        exempt = cls._pinned(
            manifest=manifest,
            pins=limits.pins,
        )
        for where, requirement in cls._requirements(manifest=manifest):
            if cls._bounded(
                requirement=requirement,
                ceilings=limits.ceilings,
                exempt=exempt,
            ):
                continue
            yield Violation(
                path=path,
                line=cls._line(
                    text=text,
                    requirement=requirement,
                ),
                column=FIRST,
                code=CODE,
                message=(
                    f"{where}: у {requirement!r} нет потолка; закрепи (==) или ограничь "
                    f"(>=x,<y), иначе версию выберет решатель"
                ),
            )

    @classmethod
    def _bounded(
        cls,
        *,
        requirement: str,
        ceilings: tuple[str, ...],
        exempt: frozenset[str],
    ) -> bool:
        stated = cls._stated(requirement=requirement)
        if stated is None:
            return True
        if any(ceiling in stated for ceiling in ceilings):
            return True
        return not stated and cls._name(requirement=requirement) in exempt

    @staticmethod
    def _stated(*, requirement: str) -> str | None:
        """Спецификаторы требования, или None, если это не то, что мы читаем.

        Маркеры отрезаются первыми: `; python_version < "3.13"` несёт свои
        операторы сравнения и ничего не говорит о том, какая версия встанет.
        """
        written = requirement.split(MARKERS, maxsplit=1)[0].strip()
        found = REQUIREMENT.match(written)
        return None if found is None else found.group("rest").strip()

    @staticmethod
    def _name(*, requirement: str) -> str:
        found = REQUIREMENT.match(requirement.split(MARKERS, maxsplit=1)[0].strip())
        return "" if found is None else found.group("name").lower().replace("_", "-")

    @staticmethod
    def _pinned(
        *,
        manifest: dict[str, Any],
        pins: tuple[str, ...],
    ) -> frozenset[str]:
        """Имена, чей источник — коммит: это потолок в одну версию."""
        sources = manifest.get("tool", {}).get("uv", {}).get("sources", {})
        return frozenset(
            name.lower().replace("_", "-")
            for name, source in sources.items()
            if isinstance(source, dict) and any(pin in source for pin in pins)
        )

    @staticmethod
    def _requirements(*, manifest: dict[str, Any]) -> list[tuple[str, str]]:
        """Каждое требование файла вместе с группой, в которой оно написано."""
        project = manifest.get("project", {})
        listed: list[tuple[str, str]] = [
            ("project.dependencies", one) for one in project.get("dependencies", [])
        ]
        for extra, group in project.get("optional-dependencies", {}).items():
            listed += [(f"project.optional-dependencies.{extra}", one) for one in group]
        for name, group in manifest.get("dependency-groups", {}).items():
            # Группа может включать другую группу — это словарь, а не
            # требование, и ограничивать в нём нечего.
            listed += [(f"dependency-groups.{name}", one) for one in group if isinstance(one, str)]
        listed += [
            ("build-system.requires", one)
            for one in manifest.get("build-system", {}).get("requires", [])
        ]
        return listed

    @staticmethod
    def _line(
        *,
        text: str,
        requirement: str,
    ) -> int:
        """Строка, на которой требование написано: tomllib позиций не отдаёт."""
        for number, line in enumerate(text.splitlines(), start=FIRST):
            if requirement in line:
                return number
        return FIRST
