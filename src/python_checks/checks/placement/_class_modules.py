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

SEPARATOR: Final = "/"


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
    def run(cls, *, file: ParsedFile, settings: CheckSettings) -> Iterator[Violation]:
        policies = settings_as(settings=settings, model=ClassModulesSettings, code=CODE).policies
        where = place(file=file)
        if where is None:
            return
        policy = cls._policy(where=where, policies=policies)
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
        """Политика самого длинного совпавшего пути.

        `application/services` важнее, чем `services`: чем длиннее путь, тем
        точнее сказано, о какой директории речь.
        """
        matched = [
            (directory, allowed)
            for directory, allowed in policies.items()
            if cls._inside(where=where, directory=directory)
        ]
        if not matched:
            return None
        return max(matched, key=lambda policy: len(policy[0].split(SEPARATOR)))

    @staticmethod
    def _inside(*, where: Place, directory: str) -> bool:
        """Идут ли эти директории подряд в пути файла."""
        wanted = tuple(directory.split(SEPARATOR))
        # Последний кусок адреса — имя самого файла, директорией он не является.
        parts = where.parts[:-1]
        span = len(wanted)
        return any(parts[start : start + span] == wanted for start in range(len(parts) - span + 1))
