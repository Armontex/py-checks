"""Директория объявляет, что в ней живёт."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Final

from python_checks.checks._kind import Kind, declarations
from python_checks.checks._location import place
from python_checks.checks.placement._marker import MARKER
from python_checks.config import CheckSettings
from python_checks.core import Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from python_checks.checks._location import Place
    from python_checks.core import ParsedFile

CODE: Final = "class-modules"


class ClassModulesSettings(CheckSettings):
    policies: dict[str, tuple[Kind, ...]] = {}


class ClassModules:
    """Падает, если в модуле лежит то, чего его директория не допускает.

    Директория называет, что в ней живёт, и рядом не садится ничего другого.
    Хелпер, заехавший в модуль use case, — либо часть класса, и тогда он
    статический метод внутри, либо общий, и тогда ему место там, где лежит
    остальное общее. Перечисление, забредшее в `dto/`, — та же история.

    Импорты, константы, блоки `if TYPE_CHECKING` и докстринг разрешены везде:
    правило про то, что модуль объявляет, а не про то, чем он пользуется.

    Ключ политики — путь, а не имя директории, и это важно: `application/
    services` держит класс-оркестратор, а `domain/services` — функции, правила,
    сравнивающие два факта. Одно слово, два разных зверя. Директории, которой
    в таблице нет, правило не касается.

    Настройка: `policies`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = ClassModulesSettings
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(
        cls,
        *,
        file: ParsedFile,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        policies = settings_as(
            settings=settings,
            model=ClassModulesSettings,
            code=CODE,
        ).policies
        where = place(file=file)
        if where is None:
            return
        policy = cls._policy(
            where=where,
            policies=policies,
        )
        if policy is None:
            return
        directory, allowed = policy
        for declared in declarations(tree=file.tree):
            # Вид не виден — судить не о чем: это класс с базой из другого модуля.
            if declared.kind is None or declared.kind in allowed:
                continue
            yield Violation.from_node(
                node=declared.node,
                path=file.path,
                code=CODE,
                message=(
                    f"{declared.name} — {declared.kind.said}; в {directory} держат "
                    f"{', '.join(sorted(one.said for one in allowed))}"
                ),
            )

    @classmethod
    def _policy(
        cls,
        *,
        where: Place,
        policies: dict[str, tuple[Kind, ...]],
    ) -> tuple[str, tuple[Kind, ...]] | None:
        """Политика самой внутренней из совпавших директорий.

        Побеждает самая глубокая: `modules/betslip/application/services`
        важнее, чем `application`. При равной глубине — более длинный ключ:
        путь говорит о месте больше, чем одно имя.
        """
        matched = [
            (depth, directory, allowed)
            for directory, allowed in policies.items()
            if (depth := where.within(directory=directory)) is not None
        ]
        if not matched:
            return None
        deepest = max(matched, key=lambda policy: (policy[0], len(policy[1])))
        return deepest[1], deepest[2]
