"""Модуль объявляет тот класс, ради которого его директория существует."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Final

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

CODE: Final = "required-class"

# Вид объявления, которому позволено стоять выше требуемого класса. Алиас и
# перечисление — словарь, а не второй предмет разговора: тело класса
# выполняется в момент объявления, поэтому имена, которые требуемый класс
# называет у себя внутри, ниже него написать нельзя.
VOCABULARY: Final[frozenset[Kind]] = frozenset({Kind.ALIAS, Kind.ENUM})


class RequiredClassSettings(CheckSettings):
    suffixes: dict[str, str] = {}


class RequiredClass:
    """Падает, если модуль не объявил класс, ради которого лежит в этой директории.

    Файл в `use_cases` существует ради сценария, файл в `repositories` — ради
    репозитория, файл в `config` — ради группы настроек. Модуль, который
    объявил что-то другое, либо назван не так, либо лежит не там.

    Класс идёт первым и идёт один. Первым — потому что читатель, открывший
    `repositories/order.py`, ищет репозиторий, а хелпер перед ним читается как
    что-то более важное. Один — потому что имя файла и есть то, как читатель
    находит класс: три сценария в одном модуле отвечают на вопрос «где
    `ResolveLimitsUseCase`» словами «прочти все три».

    Выше требуемого класса разрешены константы, алиасы и перечисления: имя
    читают там, где им пользуются, а значение вторым предметом разговора не
    становится.

    `__init__.py` ничего не объявляет, а переэкспортирует; пустой модуль ещё
    ничего не обещал; модуль с подчёркиванием (`_base.py`) держит машинерию
    своей директории, а не один из её классов. Эти трое правилу не подсудны.

    Настройка: `suffixes`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = RequiredClassSettings
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(cls, *, file: ParsedFile, settings: CheckSettings) -> Iterator[Violation]:
        suffixes = settings_as(settings=settings, model=RequiredClassSettings, code=CODE).suffixes
        where = place(file=file)
        if where is None or file.path.stem.startswith("_"):
            return
        suffix = cls._suffix(where=where, suffixes=suffixes)
        if suffix is None:
            return
        declared = list(declarations(tree=file.tree))
        if not declared:
            return
        yield from cls._violations(file=file, declared=declared, suffix=suffix)

    @classmethod
    def _violations(
        cls,
        *,
        file: ParsedFile,
        declared: list[Declaration],
        suffix: str,
    ) -> Iterator[Violation]:
        required = [one for one in declared if one.name.endswith(suffix)]
        if not required:
            yield cls._says(
                file=file,
                node=declared[0],
                message=(
                    f"модуль объявляет {cls._listed(declared=declared)}, "
                    f"а в этой директории объявляют класс ...{suffix}"
                ),
            )
            return
        if len(required) > 1:
            yield cls._says(
                file=file,
                node=required[1],
                message=(
                    f"в модуле {cls._listed(declared=required)} — "
                    f"один ...{suffix} на модуль, и модуль назван его именем"
                ),
            )
            return
        ahead = cls._ahead(declared=declared, suffix=suffix)
        if ahead is not None:
            yield cls._says(
                file=file,
                node=ahead,
                message=(
                    f"{ahead.name} объявлен выше ...{suffix}, ради которого "
                    f"существует модуль; хелперам место ниже"
                ),
            )

    @staticmethod
    def _ahead(*, declared: list[Declaration], suffix: str) -> Declaration | None:
        """Первое объявление, вставшее выше требуемого класса."""
        for one in declared:
            if one.name.endswith(suffix):
                return None
            if one.kind not in VOCABULARY:
                return one
        return None

    @staticmethod
    def _suffix(*, where: Place, suffixes: dict[str, str]) -> str | None:
        """Суффикс самой внутренней из совпавших директорий."""
        matched = [
            (depth, len(directory), suffix)
            for directory, suffix in suffixes.items()
            if (depth := where.within(directory=directory)) is not None
        ]
        return max(matched)[2] if matched else None

    @staticmethod
    def _says(*, file: ParsedFile, node: Declaration, message: str) -> Violation:
        return Violation.from_node(node=node.node, path=file.path, code=CODE, message=message)

    @staticmethod
    def _listed(*, declared: list[Declaration]) -> str:
        return ", ".join(one.name for one in declared)
