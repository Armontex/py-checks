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
        block
        for name in declared.settings
        for block in _blocks(
            model=_imported(
                path=name,
                root=root,
                src=config.src,
            ),
            seen=set(),
        )
    ]
    head = declared.header.strip() or HEADER.format(
        section=f"{prefix(source=config.origin)}{SECTION}"
    )
    return root / declared.path, "\n".join(
        [
            f"{head.rstrip()}\n",
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


def _blocks(
    *,
    model: type[BaseModel],
    seen: set[type[BaseModel]],
) -> list[str]:
    """Класс и вложенные в него секции, каждая своим куском.

    Проекту хватает назвать корневой класс: секции он и так перечислил — в
    собственных полях, — и повторять их список в настройках значит завести
    второй, который разойдётся с первым.
    """
    if model in seen:
        return []
    seen.add(model)
    lines = [f"# --- {_origin(model=model)} ---", *_commented(text=_said(model=model))]
    nested: list[str] = []
    for field in model.model_fields.values():
        section = _section(field=field)
        if section is not None:
            nested.extend(
                _blocks(
                    model=section,
                    seen=seen,
                )
            )
            continue
        name = _variable(field=field)
        if name is None:
            continue
        lines.extend(_commented(text=field.description))
        lines.append(f"{name}={_value(field=field)}")
    # Корень, у которого своих переменных нет, в файл не едет: заголовок с
    # докстрингом и пустотой под ним ничего не сообщает.
    own = [] if len(lines) == 1 or not _variables(lines=lines) else ["\n".join(lines) + "\n"]
    return own + nested


def _variables(*, lines: list[str]) -> bool:
    """Есть ли в куске хоть одна переменная, а не одни комментарии."""
    return any(not line.startswith("#") for line in lines)


def _origin(*, model: type[BaseModel]) -> str:
    """Как класс записывают в настройках: `модуль:Класс`."""
    return f"{model.__module__}{SEPARATOR}{model.__qualname__}"


def _section(*, field: FieldInfo) -> type[BaseModel] | None:
    """Вложенная секция настроек, если поле — она.

    Секция узнаётся по типу поля: `default_factory` бывает и у обычного
    значения, а модель в аннотации — это ровно «здесь начинается ещё одна
    группа переменных».
    """
    annotation = field.annotation
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    return None


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
