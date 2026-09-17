"""Сборка файла контрактов для import-linter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from python_checks.contracts._base import COMPOSITION_ROOT
from python_checks.contracts._constants import MIGRATIONS, MODULES, VERSIONS
from python_checks.contracts._layout import expressions, migrations, modules, package
from python_checks.contracts._settings import layers

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from pathlib import Path

    from python_checks.config import Config

HEADER: Final = """\
# Контракты импортов. Файл собирает `python-checks sync` из таблицы слоёв
# библиотеки и секции [tool.python-checks.layers] проекта — править его нечего,
# следующий sync перезапишет.
"""


def render(*, root: Path, config: Config) -> str | None:
    """Файл контрактов; `None`, если в проекте нечего проверять.

    Нечего — это раскладка, в которой ни один слой не найден: у библиотеки или
    у скрипта нет ни `domain`, ни `presentation`, и контракты про них были бы
    правилами ни о чём.
    """
    name = package(root=root, src=config.src)
    if name is None:
        return None
    blocks = _contracts(root=root, config=config, package=name)
    if not blocks:
        return None
    return "\n".join([HEADER, _roots(root=root, package=name), *blocks])


def _roots(*, root: Path, package: str) -> str:
    packages = [package, MIGRATIONS] if migrations(root=root) else [package]
    return _block(head="[importlinter]", keys={"root_packages": packages})


def _contracts(*, root: Path, config: Config, package: str) -> list[str]:
    table = layers(config=config)
    known = frozenset(table) | COMPOSITION_ROOT
    blocks = [
        block
        for layer in sorted(table)
        if (
            block := _layer(
                root=root,
                config=config,
                package=package,
                layer=layer,
                forbidden=known - table[layer],
            )
        )
    ]
    blocks.extend(_independence(root=root, config=config, package=package))
    blocks.extend(_migrations(root=root, package=package))
    return blocks


def _layer(
    *,
    root: Path,
    config: Config,
    package: str,
    layer: str,
    forbidden: Iterable[str],
) -> str | None:
    """Контракт «этому слою нельзя вот это»."""
    sources = expressions(root=root, src=config.src, package=package, layer=layer)
    targets = [
        expression
        for other in sorted(forbidden)
        for expression in expressions(root=root, src=config.src, package=package, layer=other)
    ]
    if not sources or not targets:
        return None
    return _block(
        head=f"[importlinter:contract:layer-{layer}]",
        keys={
            "name": [f"{layer} не импортирует чужое"],
            "type": ["forbidden"],
            # Только прямые импорты. Непрямую цепочку тут проверять нечего:
            # `presentation` зовёт `application`, а `application` знает
            # `domain` — по таблице это и есть правильная работа, и запрет
            # непрямых связей запретил бы её же.
            "allow_indirect_imports": ["True"],
            "source_modules": list(sources),
            "forbidden_modules": targets,
        },
    )


def _independence(*, root: Path, config: Config, package: str) -> list[str]:
    """Модули друг о друге не знают: соседа зовут через порт, а не по имени."""
    if not modules(root=root, src=config.src, package=package):
        return []
    return [
        _block(
            head="[importlinter:contract:modules]",
            keys={
                "name": ["модули независимы"],
                "type": ["independence"],
                "modules": [f"{package}.{MODULES}.*"],
            },
        ),
    ]


def _migrations(*, root: Path, package: str) -> list[str]:
    """Миграция описывает схему, а не зовёт приложение: код уедет, схема останется.

    Смотрим только на `versions`: `env.py` — не история, а то, что её запускает,
    и метаданные моделей он импортирует по своей работе.
    """
    if not migrations(root=root):
        return []
    return [
        _block(
            head=f"[importlinter:contract:{MIGRATIONS}]",
            keys={
                "name": ["миграции не знают приложение"],
                "type": ["forbidden"],
                "source_modules": [f"{MIGRATIONS}.{VERSIONS}"],
                "forbidden_modules": [package],
            },
        ),
    ]


def _block(*, head: str, keys: Mapping[str, Sequence[str]]) -> str:
    lines = [head]
    for key, values in keys.items():
        if len(values) == 1:
            lines.append(f"{key} = {values[0]}")
            continue
        lines.append(f"{key} =")
        lines.extend(f"    {value}" for value in values)
    return "\n".join(lines) + "\n"
