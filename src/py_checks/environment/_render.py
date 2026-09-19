"""Сборка `.env.example` из классов настроек проекта."""

from __future__ import annotations

import enum
import importlib
import json
import sys
from pathlib import Path
from textwrap import wrap
from typing import TYPE_CHECKING, Any, Final

from pydantic import BaseModel, SecretStr
from pydantic_core import PydanticUndefined

from py_checks.config import ConfigError, prefix
from py_checks.environment._constants import SECTION
from py_checks.environment._settings import example

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo

    from py_checks.config import Config

HEADER: Final = """\
# Переменные окружения, которые читает сервис. Файл собирает `py-checks sync`
# из классов настроек, перечисленных в [{section}] — править его нечего,
# следующий sync перезапишет. Значение по умолчанию здесь для того, чтобы его
# было видно, а не потому, что переменную обязательно задавать.
"""

SEPARATOR: Final = ":"

# Ширина комментария: та же, по которой переносят текст в самих докстрингах.
WIDTH: Final = 77


def render(
    *,
    root: Path,
    config: Config,
) -> tuple[Path, str] | None:
    """Путь и текст файла; `None`, если проект не объявил ни одного класса."""
    declared = example(config=config)
    if not declared.settings:
        return None
    blocks = [
        _block(
            model=_imported(
                path=name,
                root=root,
                src=config.src,
            ),
            origin=name,
        )
        for name in declared.settings
    ]
    return root / declared.path, "\n".join(
        [
            HEADER.format(section=f"{prefix(source=config.origin)}{SECTION}"),
            *blocks,
        ]
    )


def _imported(
    *,
    path: str,
    root: Path,
    src: Path,
) -> type[BaseModel]:
    """Класс настроек по записи `модуль:Класс`.

    Импорт, а не чтение исходника: имя переменной — значение атрибута поля, и
    собрано оно вызовом (`AliasChoices(...)`, имя, посчитанное при создании
    класса). Прочитать его текстом значит выполнить этот вызов самому.
    """
    module, _, attribute = path.partition(SEPARATOR)
    if not attribute:
        message = f"[{SECTION}]: {path!r} — нужна запись вида `модуль:Класс`"
        raise ConfigError(message)
    _reachable(
        root=root,
        src=src,
    )
    try:
        found = getattr(importlib.import_module(module), attribute)
    except (ImportError, AttributeError) as error:
        raise ConfigError(f"[{SECTION}]: {path!r} не импортируется: {error}") from error
    if not (isinstance(found, type) and issubclass(found, BaseModel)):
        message = f"[{SECTION}]: {path!r} — не модель pydantic"
        raise ConfigError(message)
    return found


def _reachable(
    *,
    root: Path,
    src: Path,
) -> None:
    """Дать импорту найти пакет проекта, даже если проект не установлен."""
    for directory in (root / src, root):
        name = str(directory)
        if directory.is_dir() and name not in sys.path:
            sys.path.insert(0, name)


def _block(
    *,
    model: type[BaseModel],
    origin: str,
) -> str:
    """Один класс: заголовок, о чём эта секция, и её переменные."""
    lines = [f"# --- {origin} ---", *_commented(text=_said(model=model))]
    for field in model.model_fields.values():
        name = _variable(field=field)
        if name is None:
            continue
        lines.extend(_commented(text=field.description))
        lines.append(f"{name}={_value(field=field)}")
    return "\n".join(lines) + "\n"


def _said(*, model: type[BaseModel]) -> str | None:
    """Первый абзац докстринга класса: чем эта секция занимается.

    Абзац, а не строка: докстринг переносят по ширине файла, и первая строка
    обрывается на середине фразы.
    """
    if model.__doc__ is None:
        return None
    paragraph = model.__doc__.strip().split("\n\n", maxsplit=1)[0]
    return " ".join(paragraph.split()) or None


def _commented(*, text: str | None) -> list[str]:
    """Текст как комментарий, разложенный по ширине строки."""
    if not text:
        return []
    return [f"# {line}" for line in wrap(text, width=WIDTH)]


def _variable(*, field: FieldInfo) -> str | None:
    """Имя переменной, которую читает поле; `None` — если поле не переменная.

    Поле, собранное фабрикой, — вложенная секция: переменные читают её
    собственные поля, а у неё самой их нет.
    """
    if field.default_factory is not None:
        return None
    alias = field.validation_alias
    if isinstance(alias, str):
        return alias
    choices = getattr(alias, "choices", ())
    named = [choice for choice in choices if isinstance(choice, str)]
    return named[0] if named else None


def _value(*, field: FieldInfo) -> str:
    """Значение по умолчанию так, как его пишут в файле окружения."""
    default = field.default
    if default is PydanticUndefined or default is None:
        return ""
    return _written(value=default)


def _written(*, value: Any) -> str:
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, enum.Enum):
        return _written(value=value.value)
    if isinstance(value, (str, int, float, Path)):
        return str(value)
    # Составное значение pydantic-settings читает как JSON, а не как строку:
    # список, записанный через запятую, он в поле не превратит.
    return json.dumps(
        value,
        default=str,
        ensure_ascii=False,
    )
