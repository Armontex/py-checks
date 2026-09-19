"""Сборка файла контрактов для import-linter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from py_checks.config import prefix
from py_checks.contracts._constants import MIGRATIONS, MODULES, SECTION, VERSIONS
from py_checks.contracts._layout import expressions, migrations, modules, package
from py_checks.contracts._settings import contracts

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from pathlib import Path

    from py_checks.config import Config

HEADER: Final = """\
# Контракты импортов. Файл собирает `py-checks sync` из того, какие слои
# есть на диске, и из секции [{section}] — править его нечего, следующий sync
# перезапишет. Менять нужно секцию.
"""


def render(
    *,
    root: Path,
    config: Config,
) -> str | None:
    """Файл контрактов; `None`, если проверять нечего.

    Нечего — это либо проект, который не объявил ни одного слоя, либо
    раскладка, в которой объявленных слоёв нет на диске.
    """
    name = package(
        root=root,
        src=config.src,
    )
    if name is None:
        return None
    blocks = _contracts(
        root=root,
        config=config,
        package=name,
    )
    if not blocks:
        return None
    return "\n".join(
        [
            # Секция зовётся по-разному в манифесте и в своём файле настроек:
            # написать одно имя значит послать читателя не туда в половине
            # проектов.
            HEADER.format(section=f"{prefix(source=config.origin)}{SECTION}"),
            _roots(
                root=root,
                package=name,
            ),
            *blocks,
        ]
    )


def _roots(
    *,
    root: Path,
    package: str,
) -> str:
    packages = [package, MIGRATIONS] if migrations(root=root) else [package]
    return _block(
        head="[importlinter]",
        scalars={},
        lists={"root_packages": packages},
    )


def _contracts(
    *,
    root: Path,
    config: Config,
    package: str,
) -> list[str]:
    declared = contracts(config=config)
    table = declared.layers
    known = frozenset(table) | frozenset(declared.composition_root)
    blocks = [
        block
        for layer in sorted(table)
        if (
            block := _layer(
                root=root,
                config=config,
                package=package,
                layer=layer,
                forbidden=known - frozenset(table[layer]),
            )
        )
    ]
    blocks.extend(
        _independence(
            root=root,
            config=config,
            package=package,
        )
    )
    blocks.extend(
        _migrations(
            root=root,
            package=package,
        )
    )
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
    sources = expressions(
        root=root,
        src=config.src,
        package=package,
        layer=layer,
    )
    targets = [
        expression
        for other in sorted(forbidden)
        for expression in expressions(
            root=root,
            src=config.src,
            package=package,
            layer=other,
        )
    ]
    if not sources or not targets:
        return None
    return _block(
        head=f"[importlinter:contract:layer-{layer}]",
        scalars={
            "name": f"{layer} не импортирует чужое",
            "type": "forbidden",
            # Только прямые импорты. Непрямую цепочку тут проверять нечего:
            # `presentation` зовёт `application`, а `application` знает
            # `domain` — по таблице это и есть правильная работа, и запрет
            # непрямых связей запретил бы её же.
            "allow_indirect_imports": "True",
        },
        lists={"source_modules": list(sources), "forbidden_modules": targets},
    )


def _independence(
    *,
    root: Path,
    config: Config,
    package: str,
) -> list[str]:
    """Модули друг о друге не знают: соседа зовут через порт, а не по имени."""
    if not modules(
        root=root,
        src=config.src,
        package=package,
    ):
        return []
    return [
        _block(
            head="[importlinter:contract:modules]",
            scalars={"name": "модули независимы", "type": "independence"},
            lists={"modules": [f"{package}.{MODULES}.*"]},
        ),
    ]


def _migrations(
    *,
    root: Path,
    package: str,
) -> list[str]:
    """Миграция описывает схему, а не зовёт приложение: код уедет, схема останется.

    Смотрим только на `versions`: `env.py` — не история, а то, что её запускает,
    и метаданные моделей он импортирует по своей работе.
    """
    if not migrations(root=root):
        return []
    return [
        _block(
            head=f"[importlinter:contract:{MIGRATIONS}]",
            scalars={"name": "миграции не знают приложение", "type": "forbidden"},
            lists={
                "source_modules": [f"{MIGRATIONS}.{VERSIONS}"],
                "forbidden_modules": [package],
            },
        ),
    ]


def _block(
    *,
    head: str,
    scalars: Mapping[str, str],
    lists: Mapping[str, Sequence[str]],
) -> str:
    """Один раздел ini.

    Списки пишутся в столбик даже из одного значения: import-linter разбирает
    поле-список, написанное в строку, посимвольно — и ищет пакет `p`.
    """
    lines = [head, *(f"{key} = {value}" for key, value in scalars.items())]
    for key, values in lists.items():
        lines.append(f"{key} =")
        lines.extend(f"    {value}" for value in values)
    return "\n".join(lines) + "\n"
