"""Конфиг из документации — настоящий конфиг.

Пример, который не проверяют, устаревает молча: правило переименовали, а в
документе осталось старое имя, и читатель копирует то, что больше не читается.
Поэтому разобранный сервис из `docs/service.md` разбирается той же моделью,
какой библиотека читает настройки проекта.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

import pytest

from py_checks.config import load
from py_checks.contracts import contracts
from py_checks.core import available, section_of
from py_checks.environment import example

ROOT: Final = Path(__file__).resolve().parent.parent

DOCUMENTS: Final[tuple[Path, ...]] = (
    ROOT / "docs" / "service.md",
    ROOT / "docs" / "readmes" / "service.ru.md",
)

HEADINGS: Final[tuple[str, ...]] = ("## 1. One service, whole", "## 1. Сервис целиком")

BLOCK: Final = re.compile(r"```toml\n(.*?)```", re.DOTALL)


def worked(*, document: Path) -> str:
    """Первый блок TOML после заголовка с разобранным сервисом."""
    text = document.read_text(encoding="utf-8")
    start = next((text.index(one) for one in HEADINGS if one in text), None)
    assert start is not None, f"{document}: нет раздела с разобранным сервисом"
    found = BLOCK.search(text, start)
    assert found is not None, f"{document}: в разделе нет блока TOML"
    return found.group(1)


@pytest.mark.parametrize("document", DOCUMENTS, ids=lambda path: path.name)
def test_the_worked_service_is_a_config_the_library_reads(
    document: Path,
    tmp_path: Path,
) -> None:
    (tmp_path / "py-checks.toml").write_text(
        worked(document=document),
        encoding="utf-8",
    )

    config = load(root=tmp_path)

    # Каждая проверка разбирает свою секцию своей же моделью: опечатка в
    # ключе или тип не тот — исключение здесь, а не молчание у читателя.
    for check in available().listed.values():
        config.settings_for(
            code=section_of(check=check),
            model=check.Settings,
        )
    contracts(config=config)
    example(config=config)
