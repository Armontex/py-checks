"""Чтение настроек: из своего файла проекта или из `pyproject.toml`."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING, Final

from pydantic import ValidationError

from python_checks.config._config import Config, prefix
from python_checks.config._constants import PYPROJECT, SECTION, STANDALONE
from python_checks.config._errors import ConfigError

if TYPE_CHECKING:
    from pathlib import Path

    from python_checks.config._toml import TomlTable, TomlValue

# Все файлы, по которым узнаётся корень проекта. `pyproject.toml` последний:
# он у проекта есть почти всегда, а свой файл настроек лежит рядом с ним.
ANCHORS: Final[tuple[str, ...]] = (*STANDALONE, PYPROJECT)


def find_root(*, start: Path) -> Path:
    """Ближайшая папка вверх по дереву, где лежит манифест или свой файл настроек.

    Именно она считается корнем проекта: пути в конфиге и в выводе даются
    относительно неё, чтобы строка нарушения не зависела от того, откуда
    запустили проверку.
    """
    for directory in (start, *start.parents):
        if any((directory / name).is_file() for name in ANCHORS):
            return directory
    return start


def load(*, root: Path) -> Config:
    """Настройки проекта; если их нигде нет — значения по умолчанию.

    Настройки живут либо в своём файле — `python-checks.toml` или
    `pychecks.toml`, с точкой в начале или без, — либо секцией
    `[tool.python-checks]` в `pyproject.toml`. В своём файле приставки нет:
    весь файл и есть эта секция.

    Двух мест разом не бывает: это не слияние, а вопрос без ответа, и лучше
    спросить его вслух, чем молча прочитать одно и забыть про другое.
    """
    found = _found(root=root)
    if not found:
        return Config()
    if len(found) > 1:
        raise ConfigError(
            "настройки лежат в нескольких местах: "
            + ", ".join(source.name for source, _ in found)
            + "; оставь одно, иначе неизвестно, какое из них читают"
        )
    source, section = found[0]
    return _build(
        section=section,
        source=source,
    )


def _found(*, root: Path) -> list[tuple[Path, TomlTable]]:
    """Файлы, в которых настройки этого инструмента действительно есть.

    `pyproject.toml` без секции файлом настроек не считается: он лежит у
    каждого проекта, и молчаливое присутствие — не выбор автора.
    """
    found: list[tuple[Path, TomlTable]] = []
    for name in STANDALONE:
        path = root / name
        if path.is_file():
            found.append((path, _document(path=path)))
    pyproject = root / PYPROJECT
    if pyproject.is_file() and (section := _section(document=_document(path=pyproject))):
        found.append((pyproject, section))
    return found


def _document(*, path: Path) -> TomlTable:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"{path}: {error}") from error


def _section(*, document: TomlTable) -> TomlTable:
    tool = document.get("tool")
    section = tool.get(SECTION) if isinstance(tool, dict) else None
    return section if isinstance(section, dict) else {}


def _build(
    *,
    section: TomlTable,
    source: Path,
) -> Config:
    own, checks = _split(section=section)
    named = prefix(source=source)
    # В своём файле секции нет — называть в сообщении нечего, кроме файла.
    where = f" [{named.rstrip('.')}]" if named else ""
    try:
        return Config.model_validate({**own, "checks": checks, "origin": source})
    except ValidationError as error:
        raise ConfigError(f"{source}{where}: {error}") from error


def _split(*, section: TomlTable) -> tuple[TomlTable, dict[str, TomlTable]]:
    """Свои ключи отдельно, вложенные таблицы проверок отдельно."""
    own: TomlTable = {}
    checks: dict[str, TomlTable] = {}
    for key, value in section.items():
        _place(
            key=key,
            value=value,
            own=own,
            checks=checks,
        )
    return own, checks


def _place(
    *,
    key: str,
    value: TomlValue,
    own: TomlTable,
    checks: dict[str, TomlTable],
) -> None:
    if isinstance(value, dict):
        checks[key] = value
    else:
        own[key] = value
