"""Команда `doctor`: что не так с самими настройками."""

from __future__ import annotations

from collections.abc import Sized
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path
from typing import TYPE_CHECKING, Final

import typer
from rich.console import Console

from py_checks.config import ConfigError, find_root, load, prefix
from py_checks.contracts import SECTION as CONTRACTS
from py_checks.core import EXIT_OK, EXIT_VIOLATION, available, depth, section_of
from py_checks.environment import SECTION as ENV_EXAMPLE
from py_checks.mutation import SECTION as MUTATION

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.config import CheckSettings, Config, TomlValue
    from py_checks.core import Check

# Секции, которые читает не правило: сборщики файлов и мутационный гейт.
OWNED: Final[frozenset[str]] = frozenset({CONTRACTS, ENV_EXAMPLE, MUTATION})

# Ключ, называющий места: он есть у всех правил, которые работают не везде, и
# пустой список в нём означает, что правило молчит по всему дереву.
ZONES: Final = "zones"

# Сколько похожих имён предлагать в ответ на опечатку и насколько похожих:
# умолчание difflib (0.6) молчит там, где человек видит опечатку глазами.
CLOSE: Final = 2
ALIKE: Final = 0.5

SUFFIX: Final = ".py"

# Поле и причина: остальное в жалобе pydantic — служебное.
REASON: Final = 2


@dataclass(frozen=True, slots=True)
class Complaint:
    """Что не так и с чем именно."""

    said: str
    about: str


def doctor() -> None:
    """Проверить сами настройки: опечатки, мёртвые адреса, молчащие правила."""
    config = load(root=find_root(start=Path.cwd()))
    found = [
        *_unknown(config=config),
        *_ignored(config=config),
        *_silent(config=config),
        *_nowhere(config=config),
    ]
    # Длинное имя не переносится посреди слова: читателю его копировать.
    console = Console(soft_wrap=True)
    console.print(f"{config.origin or 'настройки по умолчанию'}\n", markup=False)
    for said, group in _grouped(found=found).items():
        console.print(f"  {said}", markup=False)
        for complaint in group:
            console.print(f"    {complaint.about}", markup=False)
        console.print()
    console.print(_count(found=found), markup=False)
    raise typer.Exit(code=EXIT_VIOLATION if found else EXIT_OK)


def _grouped(*, found: list[Complaint]) -> dict[str, list[Complaint]]:
    """Замечания по заголовкам, в порядке первого появления."""
    groups: dict[str, list[Complaint]] = {}
    for complaint in found:
        groups.setdefault(complaint.said, []).append(complaint)
    return groups


def _count(*, found: list[Complaint]) -> str:
    return f"замечаний — {len(found)}" if found else "ok: настройки согласованы"


def _sections() -> set[str]:
    """Имена секций, которые кто-нибудь читает: у пяти правил оно общее."""
    return {section_of(check=check) for check in available().listed.values()}


def _unknown(*, config: Config) -> Iterator[Complaint]:
    """Секция, которой не соответствует ни правило, ни сборщик."""
    known = _sections()
    named = prefix(source=config.origin)
    for section in sorted(config.checks):
        if section in known or section in OWNED:
            continue
        close = get_close_matches(
            section,
            [*known, *OWNED],
            n=CLOSE,
            cutoff=ALIKE,
        )
        said = f"; ближайшие: {', '.join(close)}" if close else ""
        yield Complaint(
            said="опечатка в имени секции",
            about=f"[{named}{section}] — такой секции нет{said}",
        )


def _ignored(*, config: Config) -> Iterator[Complaint]:
    """`ignore`, называющий правило, которого нет."""
    codes = set(available().listed)
    for code in config.ignore:
        if code in codes:
            continue
        close = get_close_matches(
            code,
            sorted(codes),
            n=CLOSE,
            cutoff=ALIKE,
        )
        said = f"; ближайшие: {', '.join(close)}" if close else ""
        yield Complaint(
            said="ignore называет несуществующее",
            about=f"{code!r} — такого правила нет{said}",
        )


def _silent(*, config: Config) -> Iterator[Complaint]:
    """Правило, у которого секция есть, а сказать ей нечего.

    Ноль нарушений в таком случае выглядит как соблюдённое соглашение, а
    означает правило, которое ничего не проверяло. Пустая секция сама по себе
    не беда: у половины правил умолчания рабочие, и `[raw-sql]` без единой
    строки запрещает ровно то, ради чего написано.
    """
    named = prefix(source=config.origin)
    for code, check in sorted(available().listed.items()):
        section = section_of(check=check)
        if not config.enabled(code=code) or section not in config.checks:
            continue
        found = _mute(
            config=config,
            code=code,
            check=check,
            named=named,
        )
        if found is not None:
            yield found


def _mute(
    *,
    config: Config,
    code: str,
    check: Check,
    named: str,
) -> Complaint | None:
    """Чем именно эта секция ничего не говорит; `None` — говорит."""
    section = section_of(check=check)
    said = "правило включено, но молчит"
    try:
        settings = config.settings_for(
            code=section,
            model=check.Settings,
        )
    except ConfigError as error:
        return Complaint(
            said="секция не читается",
            about=f"[{named}{section}] — {_first(said=str(error))}",
        )
    zones = getattr(settings, ZONES, None)
    if zones is not None and not zones:
        return Complaint(
            said=said,
            about=f"[{named}{code}] — зон не названо: судить негде",
        )
    if config.checks[section] or not _bare(model=check.Settings):
        return None
    return Complaint(
        said=said,
        about=f"[{named}{section}] — секция пуста, а умолчаний у правила нет",
    )


def _first(*, said: str) -> str:
    """Суть чужой жалобы: поле и причина, без счётчика ошибок и ссылки.

    pydantic пишет заголовок, потом поле, потом причину с типом и входным
    значением. Читателю нужны второе и третье, и то короткой строкой.
    """
    lines = [one.strip() for one in said.splitlines()[1:] if one.strip()]
    return ": ".join(one.split(" [type=")[0] for one in lines[:REASON])


def _bare(*, model: type[CheckSettings]) -> bool:
    """Правда ли, что без таблицы у правила нет ничего.

    У `module-length` умолчание — предел в строках, и пустая секция значит
    «работай как написано в библиотеке». У `model-columns` умолчания пусты:
    там пустая секция значит «ничего не проверяй».
    """
    return all(
        _nothing(value=field.get_default(call_default_factory=True))
        for field in model.model_fields.values()
    )


def _nothing(*, value: object) -> bool:
    return value is None or value == "" or (isinstance(value, Sized) and not len(value))


def _nowhere(*, config: Config) -> Iterator[Complaint]:
    """Адрес, которому на диске ничего не соответствует.

    Директорию переименовали, блок раскладки остался — и правило смотрит туда,
    где давно ничего нет, продолжая молчать по этому поводу.
    """
    places = _places(src=config.src)
    if not places:
        return
    named = prefix(source=config.origin)
    for section, address in sorted(_addressed(config=config)):
        if any(
            depth(
                parts=parts,
                path=address,
            )
            is not None
            for parts in places
        ):
            continue
        yield Complaint(
            said="адрес, которого нет на диске",
            about=f"[{named}{section}] — {address!r} не нашлось в {config.src}",
        )


def _addressed(*, config: Config) -> Iterator[tuple[str, str]]:
    """Адреса, написанные в настройках: блоки общей таблицы и списки зон.

    Только эти два: остальные ключи — имена пакетов, типов, конструкций, и
    отличить их от пути, не зная правила, нельзя. Зона внутри массива таблиц
    (`[[confined-calls.rules]]`) — та же зона, поэтому шаг внутрь.
    """
    shared = _shared()
    for section, table in config.checks.items():
        if section in OWNED:
            continue
        if section in shared:
            yield from ((section, key) for key, value in table.items() if isinstance(value, dict))
        for value in [table, *(one for one in table.values() if isinstance(one, list))]:
            yield from ((section, one) for one in _zones(value=value))


def _zones(*, value: TomlValue) -> Iterator[str]:
    """Зоны таблицы — или зоны каждой таблицы в массиве."""
    tables = value if isinstance(value, list) else [value]
    for table in tables:
        if not isinstance(table, dict):
            continue
        named = table.get(ZONES)
        if isinstance(named, list):
            yield from (one for one in named if isinstance(one, str))


def _shared() -> set[str]:
    """Секции, которые правило читает не под своим кодом: общая таблица."""
    return {
        section_of(check=check)
        for check in available().listed.values()
        if section_of(check=check) != check.code
    }


def _places(*, src: Path) -> list[tuple[str, ...]]:
    """Куски пути каждой директории и каждого модуля под корнем исходников.

    Модули считаются наравне с директориями: `exceptions` — это и папка, и
    `exceptions.py`, и для словаря отказов это одно и то же место.
    """
    if not src.is_dir():
        return []
    found = [
        path.relative_to(src).with_suffix("").parts
        for path in src.rglob("*")
        if path.is_dir() or path.suffix == SUFFIX
    ]
    # Первый кусок — корневой пакет, адреса же пишутся от него внутрь.
    return [parts[1:] for parts in found if len(parts) > 1]


def register(*, app: typer.Typer) -> None:
    app.command("doctor")(doctor)
